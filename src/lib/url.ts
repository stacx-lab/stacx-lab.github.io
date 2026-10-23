/** A path relative to the organization site root. */
export function siteUrl(path = '/'): string {
  return path.startsWith('/') ? path : '/' + path;
}

/** A path within Kinex; keeps its existing public URLs stable. */
export function url(path = '/'): string {
  return '/kinex' + siteUrl(path);
}
