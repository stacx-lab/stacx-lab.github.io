import { readFileSync, readdirSync, existsSync } from 'node:fs';

const root = new URL('../../public/blog/', import.meta.url);

/**
 * Each post owns its HTML, metadata, and assets in public/blog/<slug>/.
 * @returns {{ id: string, data: { title: string, description: string, published: string, author?: { name: string, url?: string } } }[]}
 */
export function getPosts() {
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map(({ name: id }) => {
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) throw new Error(`Invalid blog slug: ${id}`);
      const data = JSON.parse(readFileSync(new URL(`${id}/post.json`, root), 'utf8'));
      if (!existsSync(new URL(`${id}/index.html`, root))) throw new Error(`Missing blog HTML: ${id}`);
      if (typeof data.title !== 'string' || !data.title.trim() ||
          typeof data.description !== 'string' || !data.description.trim() ||
          typeof data.published !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(data.published) ||
          (data.author && typeof data.author.name !== 'string')) {
        throw new Error(`Invalid blog metadata: ${id}/post.json`);
      }
      return { id, data };
    })
    .sort((a, b) => b.data.published.localeCompare(a.data.published) || a.id.localeCompare(b.id));
}
