import rss from '@astrojs/rss';
import { getPosts } from '../lib/content';
import { site as cfg } from '../config';

export async function GET(context) {
  const posts = await getPosts();
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return rss({
    title: 'Kinex Blog',
    description: cfg.description,
    site: context.site + base.slice(1) + '/',
    items: posts.map((p) => ({
      title: p.data.title,
      pubDate: p.data.date,
      description: p.data.summary,
      link: `${base}/blog/${p.id}/`,
      categories: p.data.tags,
    })),
  });
}
