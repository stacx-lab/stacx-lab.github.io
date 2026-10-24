// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import { getPosts } from './src/lib/blog-posts.mjs';
import remarkBaseLinks from './src/lib/remark-base-links.mjs';

// Lab pages and blog stay here; legacy Kinex routes redirect to its own domain.
const site = process.env.SITE_URL || 'https://stacx-lab.github.io';

export default defineConfig({
  site,
  base: '/',
  trailingSlash: 'always',
  build: { inlineStylesheets: 'always' },
  integrations: [sitemap({ filter: (page) => !new URL(page).pathname.startsWith('/kinex/'), customPages: getPosts().map((post) => new URL(`/blog/${post.id}/`, site).href) }), mdx()],
  markdown: {
    remarkPlugins: [[remarkBaseLinks, { base: '/kinex' }]],
    shikiConfig: {
      themes: { light: 'min-light', dark: 'min-dark' },
      defaultColor: false,
      wrap: false,
    },
  },
});
