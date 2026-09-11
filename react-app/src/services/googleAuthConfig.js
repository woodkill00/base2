export const getGoogleClientId = () => {
  const value = import.meta.env.REACT_APP_GOOGLE_CLIENT_ID || '';
  return /^[a-zA-Z0-9_-]+\.apps\.googleusercontent\.com$/.test(value) ? value : '';
};
