# kinex site

Website for [Kinex](https://github.com/stacx-lab/kinex): landing page, docs, blog.
Astro (static) + Pagefind. No UI framework, about 200 lines of client JS.
Fonts: Roboto Slab (headings), Lato (body), Commit Mono (code); self-hosted via `@fontsource`, declared in `src/components/Fonts.astro`.

```sh
npm ci
npm run dev        # http://localhost:4321/  (search needs a build)
npm run build      # dist/ + pagefind index
npm run preview
npm run check      # astro check + build + internal link/anchor check
```

## Layout

```
src/config.ts                 version, tagline, install cmd, repo, nav, doc groups
src/content/docs/*.md         docs (one file = one page; index.md = /docs/)
src/content/blog/*.md         blog posts
src/data/hero-terminal.json   landing-page simulator walkthrough
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

Write plain Markdown starting at `##`. Use `.mdx` when a page needs an imported Astro component, as in `architecture.mdx`.
Link other pages as `/docs/<slug>/`; the base path is added at build time.
The sidebar, prev/next links, one-page view (`/docs/all/`) and search update automatically.

## Add a blog post

Create `src/content/blog/<slug>.md` with `title`, `date`, `summary` and `tags`. If you set `draft: true`, the post appears only in `npm run dev`.

## Release a new version

1. Bump `version` in `src/config.ts` and `package.json`.
2. Update the docs against the tagged Kinex source, and keep each page's `sources` list accurate.
3. Add a release post under `src/content/blog/`.

## Hero session demo

`Terminal.astro` replays setup and a 30-second mug-hanging walkthrough in a 372px
terminal with internal scrolling. Input, assistant replies, tool arguments, code,
and results appear one character at a time. Tool blocks use gray-blue while
streaming or executing, green on completion, and red on error. Running tools show only an indeterminate spinner; servo waits are brief.
Pause/replay, reduced-motion, and no-JavaScript transcript fallbacks are supported.

All seven camera frames come unchanged from one successful session in
`backup/new5/view-images/`: overhead, right wrist, left wrist, insertion inspection,
and final verification after release, withdrawal, and a settling wait. Sources,
checksums, and source entry references are in `public/media/demo/provenance.json`.
Dialogue and tool displays condense that session; intermediate retries are omitted and
contact is inspected before release. This is an adapted replay, not a live robot.
Setup runs in a subshell because `roboenv setup` exports into its current directory.

## Demo video

The homepage does not currently include a demo section. When a video is available, put the files in
`public/media/`, import `DemoBanner` in `src/pages/index.astro`, and use
`<DemoBanner src="/media/reel.mp4" poster="/media/reel.jpg" />`.

## Deploy

`.github/workflows/deploy.yml` builds on every push to `main` and publishes to GitHub Pages. Before the first deploy, set *Settings → Pages → Source* to
**GitHub Actions**. CI reads the site URL and base path from Pages, so forks and custom
domains work without code changes. The build is published directly from `dist/`, with the homepage at `https://stacx-lab.github.io/` and documentation at `/docs/`. Locally, the defaults are `https://stacx-lab.github.io` and `/`; override them with `SITE_URL` and `BASE_PATH`.
