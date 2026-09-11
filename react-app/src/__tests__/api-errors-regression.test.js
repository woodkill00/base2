import { describe, expect, it } from 'vitest';
import { AxiosError } from 'axios';
import { normalizeApiError } from '../lib/apiErrors';

describe('real transport error normalization', () => {
  it('keeps field validation from an Axios 422 instead of its generic message', () => {
    const error = new AxiosError(
      'Request failed with status code 422',
      'ERR_BAD_REQUEST',
      {},
      {},
      {
        status: 422,
        data: { detail: [{ loc: ['body', 'password'], msg: 'Password does not meet policy' }] },
      }
    );
    const result = normalizeApiError(error);
    expect(result.status).toBe(422);
    expect(result.fields.password).toBe('Password does not meet policy');
    expect(result.message).not.toContain('status code');
    expect(normalizeApiError(result)).toEqual(result);
  });
  it('classifies a real network error', () => {
    expect(normalizeApiError(new AxiosError('Network Error', 'ERR_NETWORK', {}, {})).code).toBe(
      'network_error'
    );
  });
  it('never displays internal server details', () => {
    const result = normalizeApiError({
      response: { status: 500, data: { detail: 'private SQL connection information' } },
    });
    expect(result.message).toBe('Server error. Please try again.');
  });
});
