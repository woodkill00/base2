import { render, act, fireEvent, screen } from '@testing-library/react';
import RecordInspector from '../components/content/RecordInspector';
let structured;
vi.mock('../components/content/RecordStructuredFields', () => ({
  default: (props) => {
    structured = props;
    return null;
  },
}));
const record = { id: 'first', version: 1, title: 'First', values: {}, history: [] };
test('late structured-field completion cannot replace another record or an unmounted account', () => {
  const onChanged = vi.fn();
  const props = { typeKey: 'article', schema: { fields: [] }, record, onChanged, onError: vi.fn() };
  const view = render(<RecordInspector {...props} />);
  const oldCompletion = structured.onChanged;
  view.rerender(<RecordInspector {...props} record={{ ...record, id: 'second' }} />);
  act(() => oldCompletion({ ...record, version: 2 }));
  expect(onChanged).not.toHaveBeenCalled();
  const currentCompletion = structured.onChanged;
  view.unmount();
  act(() => currentCompletion({ ...record, id: 'second', version: 2 }));
  expect(onChanged).not.toHaveBeenCalled();
});

test('a structured-field write started before public editing cannot replace the unsaved snapshot', () => {
  const onChanged = vi.fn();
  render(
    <RecordInspector
      typeKey="article"
      schema={{ fields: [] }}
      canEdit
      record={{ ...record, publicContent: { excerpt: '', body: 'Saved' } }}
      onChanged={onChanged}
      onError={vi.fn()}
    />
  );
  const oldCompletion = structured.onChanged;
  fireEvent.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Unsaved public copy' },
  });
  act(() =>
    oldCompletion({ ...record, version: 2, publicContent: { excerpt: '', body: 'Saved' } })
  );
  expect(onChanged).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Public body')).toHaveValue('Unsaved public copy');
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  expect(
    screen.getByRole('button', { name: 'Discard draft and reload record' })
  ).toBeInTheDocument();
});

test('a current structured-field completion is accepted when no draft or mutation is pending', () => {
  const onChanged = vi.fn();
  const current = { ...record, publicContent: { excerpt: '', body: 'Saved' } };
  render(
    <RecordInspector
      typeKey="article"
      schema={{ fields: [] }}
      canEdit
      record={current}
      onChanged={onChanged}
      onError={vi.fn()}
    />
  );
  const updated = { ...current, version: 2 };
  act(() => structured.onChanged(updated));
  expect(onChanged).toHaveBeenCalledExactlyOnceWith(updated);
});
