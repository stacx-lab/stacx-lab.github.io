// Prefix root-relative Markdown links ("/docs/x/") and raw-HTML src/href/poster with the site base path,
// so content stays portable when the base changes.
export default function remarkBaseLinks({ base = '/' } = {}) {
  const prefix = base.replace(/\/$/, '');
  const visit = (node) => {
    if ((node.type === 'link' || node.type === 'image' || node.type === 'definition')
      && typeof node.url === 'string'
      && node.url.startsWith('/') && !node.url.startsWith('//')
      && !node.url.startsWith(prefix + '/')) {
      node.url = prefix + node.url;
    }
    // Raw HTML (e.g. <video src poster>): same rule for root-relative src/href/poster.
    if (node.type === 'html' && typeof node.value === 'string') {
      node.value = node.value.replace(/\b(src|href|poster)="(\/(?!\/)[^"]*)"/g, (m, attr, url) =>
        url.startsWith(prefix + '/') ? m : `${attr}="${prefix}${url}"`);
    }
    node.children?.forEach(visit);
  };
  return (tree) => visit(tree);
}
