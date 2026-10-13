// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import remarkBaseLinks from './src/lib/remark-base-links.mjs';

// Deploy target. CI passes the values GitHub Pages reports (see deploy.yml);
// the defaults match https://stacx-lab.github.io/kinex/.
const site = process.env.SITE_URL || 'https://stacx-lab.github.io';
const base = process.env.BASE_PATH || '/kinex';

export default defineConfig({
  site,
  base,
  trailingSlash: 'always',
  integrations: [sitemap()],
  markdown: {
    remarkPlugins: [[remarkBaseLinks, { base }]],
    shikiConfig: {
      themes: { light: 'min-light', dark: 'min-dark' },
      defaultColor: false,
      wrap: false,
    },
  },
});
