export { getPosts } from './blog-posts.mjs';
export const postHref = (post: { id: string }) => `/blog/${post.id}/`;
export const publicationLabel = (month: string) => new Intl.DateTimeFormat('en', {
  month: 'short', year: 'numeric', timeZone: 'UTC',
}).format(new Date(`${month}-01T00:00:00Z`));
