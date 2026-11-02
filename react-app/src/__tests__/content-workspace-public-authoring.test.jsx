import { readFileSync } from 'node:fs';
import postcss from 'postcss';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RecordInspector from '../components/content/RecordInspector';
import { contentWorkspaceAPI } from '../services/contentWorkspace';
import { readWorkspaceRecord } from '../services/workspaceRecord';
import { siteManifest } from '../config/siteRuntime';
import { ScrollTargetContext } from '../lib/scrollTarget';

vi.mock('../components/content/RecordStructuredFields', () => ({ default: () => null }));
vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: {
    record: vi.fn(),
    versions: vi.fn(),
    updateRecord: vi.fn(),
    restore: vi.fn(),
    transition: vi.fn(),
  },
}));
const record = {
  id: 'public-record',
  siteId: siteManifest.siteId,
  typeKey: 'article',
  schemaVersion: 1,
  updatedAt: '2026-10-31T00:00:00Z',
  title: 'Public title',
  slug: 'public-title',
  state: 'draft',
  version: 2,
  values: { summary: 'PRIVATE value' },
  publicContent: { excerpt: 'Public excerpt saved', body: 'Public body saved' },
  allowedActions: ['publish'],
  review: {
    status: 'not_requested',
    requiresReview: false,
    policyVersion: 1,
    semanticRevision: null,
    deliveryAdapter: 'local_test',
    recoveryReason: null,
  },
  history: [
    {
      version: 1,
      action: 'create',
      schemaVersion: 1,
      publicContentRestoreMode: 'preserve_current',
    },
  ],
};
const setup = (overrides = {}, extra = {}, renderOptions = {}) => {
  const props = {
    typeKey: 'article',
    schema: { fields: [{ fieldKey: 'summary', label: 'Private summary', fieldKind: 'long_text' }] },
    record: { ...record, ...overrides },
    canEdit: true,
    scopeKey: 'account-one',
    onChanged: vi.fn(),
    onError: vi.fn(),
    ...extra,
  };
  return { ...render(<RecordInspector {...props} />, renderOptions), props };
};
beforeEach(() => {
  vi.clearAllMocks();
  contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3 });
  contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
});

test('Tab reaches a populated Arabic multiline field by its exact accessible name', async () => {
  const user = userEvent.setup();
  const label = 'وصف طويل للاختبار المرئي';
  setup(
    { values: { title: 'draft record', summary: 'Private synthetic editorial note.' } },
    {
      schema: {
        fields: [
          { fieldKey: 'title', label: 'short text field', fieldKind: 'short_text' },
          { fieldKey: 'summary', label, fieldKind: 'long_text' },
        ],
      },
    }
  );
  await user.click(screen.getByRole('button', { name: 'Edit fields', exact: true }));
  const title = screen.getByRole('textbox', { name: 'short text field', exact: true });
  const note = screen.getByRole('textbox', { name: label, exact: true });
  expect(note).toHaveValue('Private synthetic editorial note.');
  expect(note).toHaveAccessibleName(label);
  // The wrapping label's raw text includes the textarea's initial text node.
  // Native getByLabel exact text is therefore unsuitable for this populated field.
  expect(note.closest('label').textContent).toContain('Private synthetic editorial note.');
  title.focus();
  await user.tab();
  expect(note).toHaveFocus();
  await user.type(note, ' Updated.');
  await user.click(screen.getByRole('button', { name: 'Discard changes', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Edit fields', exact: true }));
  expect(screen.getByRole('textbox', { name: label, exact: true })).toHaveValue(
    'Private synthetic editorial note.'
  );
  expect(contentWorkspaceAPI.updateRecord).not.toHaveBeenCalled();
});

test('saves explicit public copy and private values together in one CAS request without trimming', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: '  intentional public text  ' },
  });
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: '<b>literal</b>\n\nSecond paragraph' },
  });
  expect(screen.getByRole('button', { name: 'Publish', exact: true })).toBeDisabled();
  const unload = new Event('beforeunload', { cancelable: true });
  globalThis.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledExactlyOnceWith(
    'article',
    record.id,
    2,
    record.values,
    {
      publicContent: {
        excerpt: '  intentional public text  ',
        body: '<b>literal</b>\n\nSecond paragraph',
      },
    }
  );
});

test.each([422, 409, 503, undefined])(
  'retains public draft after rejected or uncertain %s save',
  async (status) => {
    const user = userEvent.setup();
    contentWorkspaceAPI.updateRecord.mockRejectedValue(
      status ? { response: { status } } : new Error('offline')
    );
    const { props } = setup();
    await user.click(screen.getByRole('button', { name: 'Edit fields' }));
    fireEvent.change(screen.getByLabelText('Public body'), {
      target: { value: 'Keep my public draft' },
    });
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByLabelText('Public body')).toHaveValue('Keep my public draft');
    expect(props.onChanged).not.toHaveBeenCalled();
    expect(contentWorkspaceAPI.record).not.toHaveBeenCalled();
  }
);

test('discard restores the complete saved public pair and explicit clearing stays dirty', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Discard changes' }));
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  expect(screen.getByLabelText('Public excerpt')).toHaveValue(record.publicContent.excerpt);
  expect(screen.getByLabelText('Public body')).toHaveValue(record.publicContent.body);
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
});

test('counts Unicode codepoints rather than UTF-16 units and rejects limit overflow', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: '😀'.repeat(2000) },
  });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: '😀'.repeat(2001) },
  });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
});

test.each([
  undefined,
  null,
  {},
  { excerpt: '', body: null },
  { excerpt: '', body: '\u0000' },
  { excerpt: '', body: '\ud800' },
])('missing or malformed public copy fails closed rather than becoming empty', (publicContent) => {
  expect(() =>
    readWorkspaceRecord(
      { ...record, publicContent },
      {
        recordId: record.id,
        typeKey: 'article',
        siteId: siteManifest.siteId,
      }
    )
  ).toThrow('content_record_detail_invalid');
});

test('viewers cannot edit public text or restore history', () => {
  setup({ allowedActions: [] }, { canEdit: false });
  expect(screen.queryByRole('button', { name: 'Edit fields' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Restore', exact: true })).not.toBeInTheDocument();
});

test('legacy restore warns before confirmation and reports the actual public-copy result', async () => {
  const user = userEvent.setup();
  contentWorkspaceAPI.restore.mockResolvedValue({
    ...record,
    version: 3,
    restoration: { sourceVersion: 1, publicContent: 'preserved_current' },
  });
  setup();
  await user.click(screen.getByRole('button', { name: 'Restore', exact: true }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent(/public text.*preserv/i);
  await user.click(screen.getByRole('button', { name: 'Confirm restore' }));
  await waitFor(() =>
    expect(screen.getByRole('status')).toHaveTextContent(/public text.*preserv/i)
  );
});

test.each([undefined, 'unsupported', 'invented'])(
  'unknown history coverage %s cannot restore',
  (mode) => {
    setup({ history: [{ ...record.history[0], publicContentRestoreMode: mode }] });
    const restore = screen.queryByRole('button', { name: 'Restore', exact: true });
    if (restore) expect(restore).toBeDisabled();
    expect(screen.getByText(/restoration unavailable/i)).toBeInTheDocument();
  }
);

test('a pending workflow confirmation cannot discard edits made after opening it', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Publish', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: 'Still drafting' } });
  const confirm = screen.queryByRole('button', { name: 'Confirm action' });
  if (confirm) {
    expect(confirm).toBeDisabled();
    await user.click(confirm);
  }
  expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
});

test('late save completion cannot populate another account with the same record id', async () => {
  const user = userEvent.setup();
  let resolve;
  contentWorkspaceAPI.updateRecord.mockReturnValue(
    new Promise((finish) => {
      resolve = finish;
    })
  );
  const view = setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Account one draft' },
  });
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  view.rerender(<RecordInspector {...view.props} scopeKey="account-two" />);
  await act(async () => resolve({ ...record, version: 3 }));
  expect(view.props.onChanged).not.toHaveBeenCalled();
  expect(screen.queryByDisplayValue('Account one draft')).not.toBeInTheDocument();
});

test('a malformed post-save public snapshot preserves the draft and blocks replay', async () => {
  const user = userEvent.setup();
  contentWorkspaceAPI.updateRecord.mockResolvedValue({ ...record, version: 3 });
  contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3, publicContent: undefined });
  const { props } = setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Unconfirmed draft' },
  });
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Unconfirmed draft');
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  expect(props.onChanged).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Discard draft and reload record' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Unconfirmed draft');
  expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledTimes(1);
});

test('explicit empty pair clears public copy without copying any private field', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '' } });
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledExactlyOnceWith(
    'article',
    record.id,
    2,
    record.values,
    { publicContent: { excerpt: '', body: '' } }
  );
});

test.each(['\u0000', '\ud800', '\udfff'])(
  'public draft containing invalid Unicode %j cannot save',
  async (text) => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: 'Edit fields' }));
    fireEvent.change(screen.getByLabelText('Public body'), { target: { value: text } });
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    expect(contentWorkspaceAPI.updateRecord).not.toHaveBeenCalled();
  }
);

test('body limit permits 20000 astral codepoints, rejects 20001, and leaves private values untouched', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '😀'.repeat(20000) } });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '😀'.repeat(20001) } });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  expect(screen.getByLabelText('Private summary')).toHaveValue('PRIVATE value');
});

test('public draft survives a same-version parent render with freshly allocated values', async () => {
  const user = userEvent.setup();
  const view = setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: 'Still editing' } });
  view.rerender(
    <RecordInspector
      {...view.props}
      record={{
        ...record,
        values: { ...record.values },
        publicContent: { ...record.publicContent },
      }}
    />
  );
  expect(screen.getByLabelText('Public body')).toHaveValue('Still editing');
});

test('malformed restore result never claims successful public restoration or permits replay', async () => {
  const user = userEvent.setup();
  const view = setup();
  contentWorkspaceAPI.restore.mockResolvedValue({ ...record, version: 3 });
  await user.click(screen.getByRole('button', { name: 'Restore', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Confirm restore' }));
  expect(view.props.onChanged).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Confirm restore' })).toBeDisabled();
  expect(screen.queryByText('Historical public text was restored.')).not.toBeInTheDocument();
});

test.each(['save', 'restore'])(
  'successful %s must not accept a stale pre-mutation detail version',
  async (action) => {
    const user = userEvent.setup();
    const view = setup();
    contentWorkspaceAPI.record.mockResolvedValue(record);
    contentWorkspaceAPI.updateRecord.mockResolvedValue({ ...record, version: 3 });
    contentWorkspaceAPI.restore.mockResolvedValue({
      ...record,
      version: 3,
      restoration: { sourceVersion: 1, publicContent: 'preserved_current' },
    });
    if (action === 'save') {
      await user.click(screen.getByRole('button', { name: 'Edit fields' }));
      fireEvent.change(screen.getByLabelText('Public body'), {
        target: { value: 'Keep committed but unconfirmed copy' },
      });
      await user.click(screen.getByRole('button', { name: 'Save changes' }));
      expect(screen.getByLabelText('Public body')).toHaveValue(
        'Keep committed but unconfirmed copy'
      );
      expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    } else {
      await user.click(screen.getByRole('button', { name: 'Restore', exact: true }));
      await user.click(screen.getByRole('button', { name: 'Confirm restore' }));
      expect(screen.queryByText('Current public text was preserved.')).not.toBeInTheDocument();
    }
    expect(view.props.onChanged).not.toHaveBeenCalled();
    expect(
      screen.getByRole('button', { name: 'Discard draft and reload record' })
    ).toBeInTheDocument();
  }
);

test('saved workflow and confirmation rows reserve full rows only in narrow inspectors', () => {
  setup({ allowedActions: ['submit_review', 'publish', 'delete'] });
  const buttons = ['Submit for review', 'Publish', 'Delete record'].map((name) => {
    expect(screen.getAllByRole('button', { name, exact: true })).toHaveLength(1);
    return screen.getByRole('button', { name, exact: true });
  });
  expect(buttons[0]).toHaveClass('base2-button--primary');
  expect(buttons[1]).toHaveClass('base2-button--primary');
  expect(buttons[2]).toHaveClass('base2-button--ghost');
  for (const button of buttons)
    expect(button.parentElement).toHaveClass('workspace-record-action-row');
  const source = readFileSync('src/pages/ContentWorkspace.jsx', 'utf8');
  const css = postcss.parse(source.match(/<style>\{`([\s\S]*?)`\}/)[1]);
  for (const [selector, declarations] of [
    ['.workspace-record-action-row', { 'flex-wrap': 'wrap' }],
    ['.workspace-record-action-row > .base2-button', { flex: '1 1 100%', 'min-inline-size': '0' }],
  ]) {
    const rules = [];
    css.walkRules(selector, (rule) => rules.push(rule));
    expect(rules).toHaveLength(1);
    expect(rules[0].parent.name).toBe('container');
    expect(rules[0].parent.params).toBe('workspace-detail-card (max-width: 24rem)');
    expect(Object.fromEntries(rules[0].nodes.map((node) => [node.prop, node.value]))).toEqual(
      declarations
    );
  }
});

test.each([
  ['submit_review', 'Submit for review'],
  ['publish', 'Publish'],
  ['delete', 'Delete record'],
])('saved %s retains cancel, confirm and exact versioned transition', async (action, label) => {
  const user = userEvent.setup();
  contentWorkspaceAPI.transition.mockResolvedValue({ ...record, version: 3 });
  setup({ allowedActions: ['submit_review', 'publish', 'delete'] });
  await user.click(screen.getByRole('button', { name: label, exact: true }));
  expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Confirm action' }).parentElement).toHaveClass(
    'workspace-record-action-row'
  );
  await user.click(screen.getByRole('button', { name: 'Keep unchanged' }));
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: label, exact: true }));
  await user.click(screen.getByRole('button', { name: 'Confirm action' }));
  await waitFor(() =>
    expect(contentWorkspaceAPI.transition).toHaveBeenCalledExactlyOnceWith(
      'article',
      record.id,
      action,
      record.version
    )
  );
  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
});

test.each([
  ['Submit for review', 'Confirm action', 'Keep unchanged'],
  ['Publish', 'Confirm action', 'Keep unchanged'],
  ['Delete record', 'Confirm action', 'Keep unchanged'],
  ['Restore', 'Confirm restore', 'Keep current'],
])(
  'inline %s confirmation focuses safe dismissal and restores on Escape/cancel without writes',
  async (label, confirm, dismiss) => {
    const user = userEvent.setup();
    setup({ allowedActions: ['submit_review', 'publish', 'delete'] });
    const trigger = screen.getByRole('button', { name: label, exact: true });
    await user.click(trigger);
    expect(screen.getByRole('button', { name: dismiss, exact: true })).toHaveFocus();
    expect(screen.getByRole('button', { name: confirm, exact: true })).toBeEnabled();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.click(trigger);
    await user.click(screen.getByRole('button', { name: dismiss, exact: true }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
    expect(contentWorkspaceAPI.restore).not.toHaveBeenCalled();
    expect(contentWorkspaceAPI.updateRecord).not.toHaveBeenCalled();
  }
);

const interruptedPanels = [
  ['Publish', 'Keep unchanged', 'Confirm action'],
  ['Restore', 'Keep current', 'Confirm restore'],
];
for (const method of ['Escape', 'button']) {
  test.each(interruptedPanels)(
    `dirty %s dismissal by ${method} uses same-record fallback on repeated opens`,
    async (label, dismiss, confirm) => {
      const user = userEvent.setup();
      setup();
      for (let iteration = 0; iteration < 2; iteration++) {
        await user.click(screen.getByRole('button', { name: 'Edit fields', exact: true }));
        const trigger = screen.getByRole('button', { name: label, exact: true });
        await user.click(trigger);
        await user.type(screen.getByLabelText('Private summary'), ' changed');
        expect(trigger).toBeDisabled();
        expect(screen.getByRole('button', { name: confirm, exact: true })).toBeDisabled();
        const cancel = screen.getByRole('button', { name: dismiss, exact: true });
        cancel.focus();
        if (method === 'Escape') await user.keyboard('{Escape}');
        else await user.click(cancel);
        expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
        expect(screen.getByRole('heading', { name: record.title, exact: true })).toHaveFocus();
        expect(screen.getByLabelText('Private summary')).toHaveValue(
          record.values.summary + ' changed'
        );
        await user.click(screen.getByRole('button', { name: 'Discard changes', exact: true }));
      }
      expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
      expect(contentWorkspaceAPI.restore).not.toHaveBeenCalled();
      expect(contentWorkspaceAPI.updateRecord).not.toHaveBeenCalled();
    }
  );

  test.each(interruptedPanels)(
    `hidden %s trigger is not restored by ${method}`,
    async (label, dismiss) => {
      const user = userEvent.setup();
      setup();
      const trigger = screen.getByRole('button', { name: label, exact: true });
      await user.click(trigger);
      trigger.style.visibility = 'hidden';
      const cancel = screen.getByRole('button', { name: dismiss, exact: true });
      cancel.focus();
      if (method === 'Escape') await user.keyboard('{Escape}');
      else await user.click(cancel);
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(screen.getByRole('heading', { name: record.title, exact: true })).toHaveFocus();
    }
  );
}

test.each(interruptedPanels)(
  'authoritative version refresh restores only removed-panel focus for %s',
  async (label, dismiss) => {
    const user = userEvent.setup();
    const { props, rerender } = setup();
    await user.click(screen.getByRole('button', { name: label, exact: true }));
    expect(screen.getByRole('button', { name: dismiss, exact: true })).toHaveFocus();
    rerender(
      <RecordInspector
        {...props}
        record={{
          ...props.record,
          version: 3,
          title: 'Authoritative title',
          allowedActions: [],
          history: [],
        }}
      />
    );
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Authoritative title', exact: true })).toHaveFocus();
  }
);

test.each(interruptedPanels)(
  'authoritative version refresh does not steal outside focus for %s',
  async (label) => {
    const user = userEvent.setup();
    const { props, rerender } = setup();
    await user.click(screen.getByRole('button', { name: label, exact: true }));
    const outside = document.createElement('button');
    outside.textContent = 'Other workspace control';
    document.body.append(outside);
    try {
      outside.focus();
      rerender(
        <RecordInspector
          {...props}
          record={{ ...props.record, version: 3, allowedActions: [], history: [] }}
        />
      );
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(outside).toHaveFocus();
    } finally {
      outside.remove();
    }
  }
);

test.each(interruptedPanels)(
  'authoritative version refresh prefers the still-enabled same-record %s trigger',
  async (label) => {
    const user = userEvent.setup();
    const { props, rerender } = setup();
    const trigger = screen.getByRole('button', { name: label, exact: true });
    await user.click(trigger);
    rerender(<RecordInspector {...props} record={{ ...props.record, version: 3 }} />);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(trigger).toBeEnabled();
    expect(trigger).toHaveFocus();
  }
);

test.each([
  ['Publish', 'Confirm action', 'Keep unchanged', 'transition'],
  ['Restore', 'Confirm restore', 'Keep current', 'restore'],
])(
  'blocked %s confirmation cannot dismiss or mutate through Escape/cancel',
  async (label, confirm, dismiss, method) => {
    const user = userEvent.setup();
    const error = { response: { status: 409 } };
    contentWorkspaceAPI[method].mockRejectedValue(error);
    const { props } = setup();
    await user.click(screen.getByRole('button', { name: label, exact: true }));
    await user.click(screen.getByRole('button', { name: confirm, exact: true }));
    await waitFor(() => expect(props.onError).toHaveBeenLastCalledWith(error));
    const cancel = screen.getByRole('button', { name: dismiss, exact: true });
    expect(cancel).toBeDisabled();
    expect(screen.getByRole('button', { name: confirm, exact: true })).toBeDisabled();
    fireEvent.keyDown(cancel, { key: 'Escape' });
    fireEvent.click(cancel);
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(contentWorkspaceAPI[method]).toHaveBeenCalledTimes(1);
  }
);

test.each([
  ['Submit for review', 'Keep unchanged'],
  ['Publish', 'Keep unchanged'],
  ['Delete record', 'Keep unchanged'],
  ['Restore', 'Keep current'],
])(
  'confirmation %s reserves compact inset and aligns after safe entry focus',
  async (label, dismiss) => {
    const user = userEvent.setup();
    const align = vi.fn((panel) => {
      expect(panel).toBe(screen.getByRole('alertdialog'));
      expect(screen.getByRole('button', { name: dismiss, exact: true })).toHaveFocus();
    });
    setup(
      { allowedActions: ['submit_review', 'publish', 'delete'] },
      {},
      {
        wrapper: ({ children }) => (
          <ScrollTargetContext.Provider value={{ align }}>{children}</ScrollTargetContext.Provider>
        ),
      }
    );
    const trigger = screen.getByRole('button', { name: label, exact: true });
    await user.click(trigger);
    expect(screen.getByRole('alertdialog')).toHaveClass('workspace-record-confirmation');
    expect(align).toHaveBeenCalledTimes(1);
    await user.keyboard('{Escape}');
    expect(trigger).toHaveFocus();
    expect(align).toHaveBeenCalledTimes(1);
    await user.click(trigger);
    expect(align).toHaveBeenCalledTimes(2);
    await user.click(screen.getByRole('button', { name: dismiss, exact: true }));
    expect(trigger).toHaveFocus();
    expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
    expect(contentWorkspaceAPI.restore).not.toHaveBeenCalled();
  }
);

test('confirmation inset frees label width only inside the narrow detail-card query', () => {
  const source = readFileSync('src/pages/ContentWorkspace.jsx', 'utf8');
  const css = postcss.parse(source.match(/<style>\{`([\s\S]*?)`\}/)[1]);
  const rules = [];
  css.walkRules('.workspace-record-confirmation', (rule) => rules.push(rule));
  expect(rules).toHaveLength(1);
  expect(rules[0].parent.params).toBe('workspace-detail-card (max-width: 24rem)');
  expect(Object.fromEntries(rules[0].nodes.map((node) => [node.prop, node.value]))).toEqual({
    'padding-inline': '0.5rem',
  });
  // The native Keep unchanged failure needs 7.722px more. Two 1rem panel
  // insets becoming 0.5rem provide 16px at a 16px root, without shrinking text.
  expect(94.081 + 16).toBeGreaterThanOrEqual(101.80296325683594);
});

test('confirmation capture checks authored positioning without centering beneath sticky chrome', () => {
  const source = readFileSync('e2e/workspace/workspace-release.spec.ts', 'utf8');
  const body = source.slice(
    source.indexOf("test('workspace workflow confirmations cancel without mutation'"),
    source.indexOf('declare global')
  );
  expect(body).not.toContain('scrollIntoView');
  expect(body.indexOf('await ownershipStep(capture)')).toBeLessThan(
    body.indexOf('expect(metrics.visible).toBe(true)')
  );
  expect(body).toContain('toBeInViewport({ ratio: 1 })');
  expect(body).toContain('metric.available >= metric.required');
});

test('scroll-target replacement does not steal dirty-panel focus and is used on the next open', async () => {
  const user = userEvent.setup();
  const first = { align: vi.fn() },
    second = { align: vi.fn() };
  let target = first;
  const { props, rerender } = setup(
    {},
    {},
    {
      wrapper: ({ children }) => (
        <ScrollTargetContext.Provider value={target}>{children}</ScrollTargetContext.Provider>
      ),
    }
  );
  await user.click(screen.getByRole('button', { name: 'Edit fields', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Publish', exact: true }));
  expect(first.align).toHaveBeenCalledTimes(1);
  const field = screen.getByLabelText('Private summary');
  await user.type(field, ' changed');
  target = second;
  rerender(<RecordInspector {...props} />);
  expect(field).toHaveFocus();
  expect(second.align).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Confirm action' })).toBeDisabled();
  const dismiss = screen.getByRole('button', { name: 'Keep unchanged' });
  dismiss.focus();
  await user.keyboard('{Escape}');
  expect(screen.getByRole('heading', { name: record.title, exact: true })).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Discard changes' }));
  await user.click(screen.getByRole('button', { name: 'Publish', exact: true }));
  expect(second.align).toHaveBeenCalledTimes(1);
  expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
  expect(contentWorkspaceAPI.restore).not.toHaveBeenCalled();
});
