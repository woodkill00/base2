// Normalizes axios/FastAPI/Django-ish error shapes into a single UI-friendly form.

const _isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

const _stringOrNull = (v) => (typeof v === 'string' && v.trim() ? v : null);

const _pickMessage = (data) => {
  if (!_isObject(data)) {
    return null;
  }
  return (
    _stringOrNull(data.message) ||
    _stringOrNull(data.detail) ||
    _stringOrNull(data.error) ||
    null
  );
};

const _fieldsFromFastApi422 = (detail) => {
  if (!Array.isArray(detail)) {
    return null;
  }

  const fields = {};
  for (const item of detail) {
    if (!_isObject(item)) {
      continue;
    }
    const msg = _stringOrNull(item.msg);
    const loc = Array.isArray(item.loc) ? item.loc : null;
    const key = loc && loc.length ? String(loc[loc.length - 1]) : null;
    if (key && msg) {
      fields[key] = msg;
    }
  }

  return Object.keys(fields).length ? fields : null;
};

const _guessFieldsFromAuthMessage = (message, url, status) => {
  const m = String(message || '');
  const u = String(url || '');

  if (status === 401 && /invalid credentials/i.test(m)) {
    return { password: 'Invalid email or password' };
  }

  if (status === 403 && /inactive/i.test(m) && u.includes('/auth/login')) {
    return { email: 'Account inactive' };
  }

  return null;
};

export const normalizeApiError = (error, opts = {}) => {
  const fallbackMessage =
    _stringOrNull(opts.fallbackMessage) ||
    'Something went wrong. Please try again.';

  // Already normalized?
  if (_isObject(error) && _stringOrNull(error.message) && _isObject(error.fields || {}) ) {
    return {
      code: error.code || 'error',
      message: error.message,
      fields: error.fields || null,
      status: error.status || null,
    };
  }

  const status = error?.response?.status ?? null;
  const data = error?.response?.data;
  const url = error?.config?.url;

  // Network / CORS / timeout-ish: axios sets request but no response.
  if (error?.request && !error?.response) {
    return {
      code: 'network_error',
      message: 'Network error. Please check your connection and try again.',
      fields: null,
      status: null,
    };
  }

  const messageFromBody = _pickMessage(data);

  let fields = null;
  if (_isObject(data) && _isObject(data.fields)) {
    fields = data.fields;
  } else if (_isObject(data) && Array.isArray(data.detail)) {
    fields = _fieldsFromFastApi422(data.detail);
  }

  const message =
    messageFromBody ||
    (status === 503
      ? 'Service unavailable. Please try again shortly.'
      : status === 500
        ? 'Server error. Please try again.'
        : fallbackMessage);

  if (!fields) {
    fields = _guessFieldsFromAuthMessage(message, url, status);
  }

  return {
    code: _stringOrNull(data?.code) || (status ? `http_${status}` : 'error'),
    message,
    fields: fields || null,
    status,
  };
};
