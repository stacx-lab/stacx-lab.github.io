/** Join a root-relative path with the configured base: url('/docs/') → '/kinex/docs/'. */
export function url(path = '/'): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return base + (path.startsWith('/') ? path : '/' + path);
}
