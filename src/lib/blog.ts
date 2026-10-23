import { getCollection, type CollectionEntry } from 'astro:content';

export type Post = CollectionEntry<'blog'>;
export const postHref = (post: Post) => `/blog/${post.id}/`;
export const getPosts = async () => (await getCollection('blog')).sort((a, b) =>
  b.data.published.localeCompare(a.data.published) || a.id.localeCompare(b.id));
export const publicationLabel = (month: string) => new Intl.DateTimeFormat('en', {
  month: 'short', year: 'numeric', timeZone: 'UTC',
}).format(new Date(`${month}-01T00:00:00Z`));
