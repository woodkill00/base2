const HOST_LABEL = /^(?:admin|swagger|traefik|pgadmin|flower)$/;
const DOMAIN = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;
const CONTROL = /[\x00-\x1f\x7f]/;

export const installOwnerEdgeAuth = async (
  context,
  { domain, username, password, hosts }
) => {
  if (!DOMAIN.test(domain) || CONTROL.test(username) || CONTROL.test(password)) {
    throw new Error('owner edge authentication inputs are invalid');
  }
  if (!username || !password || !Array.isArray(hosts) || hosts.length < 1) {
    throw new Error('owner edge authentication inputs are incomplete');
  }
  const allowed = new Set(
    hosts.map((host) => {
      if (!HOST_LABEL.test(host)) throw new Error('owner edge host is not allowlisted');
      return `${host}.${domain}`;
    })
  );
  const authorization = `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}`;
  await context.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.protocol === 'https:' && allowed.has(url.hostname) && (!url.port || url.port === '443')) {
      await route.continue({
        headers: { ...request.headers(), Authorization: authorization },
      });
      return;
    }
    await route.continue();
  });
};

