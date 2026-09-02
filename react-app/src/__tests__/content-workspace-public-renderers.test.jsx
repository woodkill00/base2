import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import PublicFieldRenderer, {
  PublicWorkspaceFields,
} from '../components/content/PublicFieldRenderer';
import presets from '../config/generated/content-workspace-presets.json';

expect.extend(toHaveNoViolations);

const cases = [
  ['short_text', 'Safe text', 'Safe text'],
  ['long_text', 'Long safe text', 'Long safe text'],
  ['integer', 42, '42'],
  ['decimal', '12.50', '12.50'],
  ['boolean', true, 'Yes'],
  ['date', '2026-09-02', '2026-09-02'],
  ['datetime', '2026-09-02T10:00:00Z', '2026-09-02T10:00:00Z'],
  ['enum', 'featured', 'featured'],
  ['slug', 'safe-record', 'safe-record'],
  ['email', 'safe@example.test', 'safe@example.test'],
  ['location', { locality: 'Durres', country: 'Albania' }, 'Durres, Albania'],
  ['reference', '00000000-0000-4000-8000-000000000001', 'Related record'],
  ['references', ['one', 'two'], '2 related records'],
  ['image', { altText: 'Synthetic coast' }, 'Image available'],
  ['file', { label: 'Safe brochure' }, 'Safe brochure'],
  ['json_object', { safe: true }, 'Structured information'],
];

describe('closed public workspace renderers', () => {
  test.each(cases)(
    'renders the closed %s field kind without interpreting markup',
    (fieldKind, value, expected) => {
      const { container } = render(<PublicFieldRenderer field={{ fieldKind }} value={value} />);
      expect(container).toHaveTextContent(expected);
      expect(container.querySelector('script')).toBeNull();
    }
  );

  test('renders bounded structured rich text and rejects active URLs and unknown kinds', () => {
    const { rerender } = render(
      <PublicFieldRenderer field={{ fieldKind: 'url' }} value="javascript:alert(1)" />
    );
    expect(screen.getByText('Unavailable link')).toBeVisible();
    rerender(
      <PublicFieldRenderer
        field={{ fieldKind: 'rich_text' }}
        value={{ type: 'paragraph', children: [{ type: 'text', text: '<img onerror=alert(1)>' }] }}
      />
    );
    expect(screen.getByText('<img onerror=alert(1)>')).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
    rerender(<PublicFieldRenderer field={{ fieldKind: 'executable' }} value="unsafe" />);
    expect(screen.queryByText('unsafe')).not.toBeInTheDocument();
  });

  test('renders only declared bounded public projections and remains accessible', async () => {
    const item = {
      metadata: {
        workspaceFields: [
          { fieldKey: 'title', label: 'Title', fieldKind: 'short_text' },
          { fieldKey: 'available', label: 'Available', fieldKind: 'boolean' },
        ],
        workspaceValues: { title: 'Safe listing', available: true, private_note: 'never render' },
      },
    };
    const rendered = render(<PublicWorkspaceFields item={item} />);
    expect(screen.getByText('Safe listing')).toBeVisible();
    expect(screen.getByText('Yes')).toBeVisible();
    expect(screen.queryByText('never render')).not.toBeInTheDocument();
    expect(await axe(rendered.container)).toHaveNoViolations();
  });

  test.each(Object.entries(presets.definitions))(
    'renders the generated %s preset through the same closed registry',
    (_presetId, definition) => {
      const values = Object.fromEntries(
        definition.fields.map((field) => [
          field.fieldKey,
          {
            boolean: true,
            integer: 2,
            decimal: '2.50',
            date: '2026-09-02',
            datetime: '2026-09-02T10:00:00Z',
            location: { locality: 'Synthetic city', country: 'Test country' },
            reference: '00000000-0000-4000-8000-000000000001',
            references: ['00000000-0000-4000-8000-000000000001'],
            image: { altText: 'Synthetic image' },
            file: { label: 'Synthetic file' },
            rich_text: { type: 'paragraph', children: [{ type: 'text', text: 'Safe body' }] },
            json_object: { safe: true },
          }[field.fieldKind] ?? 'Synthetic value',
        ])
      );
      const { container } = render(
        <PublicWorkspaceFields
          item={{ metadata: { workspaceFields: definition.fields, workspaceValues: values } }}
        />
      );
      expect(container.querySelectorAll('dt')).toHaveLength(definition.fields.length);
      expect(container.querySelector('script')).toBeNull();
    }
  );
});
