// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import remarkBaseLinks from './src/lib/remark-base-links.mjs';

// Keep local builds and CI aligned with https://stacx-lab.github.io/kinex/.
const site = process.env.SITE_URL || 'https://stacx-lab.github.io';
const base = process.env.BASE_PATH === undefined ? '/kinex' : process.env.BASE_PATH || '/';

export default defineConfig({
  site,
  base,
  trailingSlash: 'always',
  integrations: [sitemap(), mdx()],
  markdown: {
    remarkPlugins: [[remarkBaseLinks, { base }]],
    shikiConfig: {
      themes: { light: 'min-light', dark: 'min-dark' },
      defaultColor: false,
      wrap: false,
    },
  },
});
