// Do not navigate away while the server is still revoking the cookie session.
export async function completeSignOut(page) {
  const origin = new URL(page.url()).origin;
  const [response] = await Promise.all([
    page.waitForResponse((response) => {
      const url = new URL(response.url());
      return (
        url.origin === origin &&
        url.pathname === '/api/auth/logout' &&
        response.request().method() === 'POST'
      );
    }),
    page.getByRole('button', { name: 'Sign out', exact: true }).click(),
  ]);
  if (!response.ok() || (await response.finished())) throw new Error('Logout did not complete');
}
