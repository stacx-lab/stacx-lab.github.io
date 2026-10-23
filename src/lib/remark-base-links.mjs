// Resolve project-relative Markdown links and HTML assets within Kinex docs.
// Other collections use normal site-root URLs.
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
  return (tree, file) => {
    // Only Kinex docs use project-relative links. Blog links are site-relative.
    if (file.history.some((path) => /[/\\]content[/\\]docs[/\\]/.test(path))) visit(tree);
  };
}
