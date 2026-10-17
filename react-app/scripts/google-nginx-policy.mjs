import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export function googleNginxPolicy(source, clientId = '') {
  if (!clientId || clientId === 'disabled') return source;
  if (!/^[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/.test(clientId)) {
    throw new Error('Invalid Google client configuration');
  }
  const substitutions = [
    ["script-src 'self';", "script-src 'self' https://accounts.google.com/gsi/client;"],
    [
      "connect-src 'self';",
      "connect-src 'self' https://accounts.google.com/gsi/; frame-src 'self' https://accounts.google.com/gsi/;",
    ],
    [
      "style-src 'self' 'unsafe-inline';",
      "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style;",
    ],
  ];
  for (const [before, after] of substitutions) {
    if (source.split(before).length !== 2) throw new Error('Unexpected browser policy template');
    source = source.replace(before, after);
  }
  return source;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw new Error('Browser policy input/output required');
  writeFileSync(
    output,
    googleNginxPolicy(readFileSync(input, 'utf8'), process.env.REACT_APP_GOOGLE_CLIENT_ID)
  );
}
