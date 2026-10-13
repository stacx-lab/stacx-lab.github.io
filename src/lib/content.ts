import { getCollection, type CollectionEntry } from 'astro:content';
import { docGroups } from '../config';
import { url } from './url';

export type Doc = CollectionEntry<'docs'>;
export type Post = CollectionEntry<'blog'>;

/** Docs in sidebar order: group (as listed in config), then `order`. */
export async function getDocs(): Promise<Doc[]> {
  const docs = await getCollection('docs');
  const g = (d: Doc) => docGroups.indexOf(d.data.group);
  return docs.sort((a, b) => g(a) - g(b) || a.data.order - b.data.order || a.id.localeCompare(b.id));
}

export const docSlug = (d: Doc) => (d.id === 'index' ? undefined : d.id);
export const docHref = (d: Doc) => url(d.id === 'index' ? '/docs/' : `/docs/${d.id}/`);

/** Published posts, newest first. Drafts show only in `astro dev`. */
export async function getPosts(): Promise<Post[]> {
  const posts = await getCollection('blog', (p) => import.meta.env.DEV || !p.data.draft);
  return posts.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

export const postHref = (p: Post) => url(`/blog/${p.id}/`);
export const ymd = (d: Date) => d.toISOString().slice(0, 10);

/** Display form of a tag slug: "field-report" → "Field-Report". */
export const tagLabel = (t: string) => t.replace(/(^|-)([a-z])/g, (_, s, c) => s + c.toUpperCase());
