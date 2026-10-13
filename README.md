# kinex site

Website for [Kinex](https://github.com/stacx-lab/kinex): landing page, docs, blog.
Astro (static) + Pagefind. No UI framework, about 200 lines of client JS.
Fonts: Roboto Slab (headings), Lato (body), Commit Mono (code); self-hosted via `@fontsource`, declared in `src/components/Fonts.astro`.

```sh
npm ci
npm run dev        # http://localhost:4321/kinex/  (search needs a build)
npm run build      # dist/ + pagefind index
npm run preview
npm run check      # astro check + build + internal link/anchor check
```

## Layout

```
src/config.ts                 version, tagline, install cmd, repo, nav, doc groups
src/content/docs/*.md         docs (one file = one page; index.md = /docs/)
src/content/blog/*.md         blog posts
src/data/hero-terminal.json   landing-page terminal sessions
src/components/               Terminal, ArchDiagram, DemoBanner, Sidebar, Toc, Search…
src/layouts/                  Base, Doc, Post
src/styles/                   global.css (tokens, light/dark), prose.css (markdown)
```

## Add a doc page

Create `src/content/docs/<slug>.md`:

```yaml
---
title: Recording
description: One sentence.
group: Guides          # Get started | Concepts | Guides | Reference (see src/config.ts)
order: 90              # position inside the group
label: Recording       # optional sidebar label
sources: ["docs/commands.md"]   # kinex repo paths backing the page, linked at v<version>
---
```

Write plain Markdown starting at `##`. Link other pages as `/docs/<slug>/`; the base path is added at build time.
The sidebar, prev/next links, one-page view (`/docs/all/`) and search update automatically.

## Add a blog post

Create `src/content/blog/<slug>.md` with `title`, `date`, `summary` and `tags`. If you set `draft: true`, the post appears only in `npm run dev`.

## Release a new version

1. Bump `version` in `src/config.ts` and `package.json`.
2. Update the docs against the tagged Kinex source, and keep each page's `sources` list accurate.
3. Add a release post under `src/content/blog/`.

## Demo video

`src/pages/index.astro` renders `<DemoBanner />` as a placeholder. Put files in `public/media/` and use
`<DemoBanner src="/media/reel.mp4" poster="/media/reel.jpg" />`.

## Deploy

`.github/workflows/deploy.yml` builds on every push to `main` and publishes to GitHub Pages. Before the first deploy, set *Settings → Pages → Source* to
**GitHub Actions**. CI reads the site URL and base path from Pages, so forks and custom
domains work without code changes. Locally, the defaults are `https://stacx-lab.github.io` and `/kinex`; override them with `SITE_URL` and `BASE_PATH`.
