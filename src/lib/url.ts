/** A path relative to the organization site root. */
export function siteUrl(path = '/'): string {
  return path.startsWith('/') ? path : '/' + path;
}

/** A retained Kinex asset path; keeps existing media URLs stable. */
export function url(path = '/'): string {
  return '/kinex' + siteUrl(path);
}

/** A page on the current Kinex website. */
export function kinexUrl(path = '/'): string {
  return 'https://kinex-agent.org' + siteUrl(path);
}
