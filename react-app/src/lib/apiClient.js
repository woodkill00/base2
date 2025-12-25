import axios from 'axios';

// Always use relative path for API, so Traefik can route correctly
const API_URL = '/api';

const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  xsrfCookieName: 'base2_csrf',
  xsrfHeaderName: 'X-CSRF-Token',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;
