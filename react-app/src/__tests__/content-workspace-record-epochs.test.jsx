import { render, act } from '@testing-library/react';
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
