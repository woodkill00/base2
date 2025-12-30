import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.05'],
  },
};

const domain = __ENV.DOMAIN || 'localhost';

export default function () {
  const base = `https://${domain}`;
  const res1 = http.get(`${base}/api/health`, { tags: { name: 'api_health' } });
  sleep(1);
  const res2 = http.get(`${base}/openapi.json`, { tags: { name: 'openapi' } });
  sleep(1);
}
