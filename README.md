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

## Homepage video gallery

`src/components/VideoGallery.astro` sits below the hero. The two entries are defined
in `src/data/gallery.ts`; media files live in `public/media/gallery/<id>/`.

- `real-hang-mug`: the original 60-second demo, compressed without changing its
  duration, frame order, or existing speed changes.
- `yam-hang-mug`: the 30-second recording/session replay, also compressed.

Delivery MP4s retain 1080p/30 FPS (x264 slow, CRF 28, faststart); WebM fallbacks
use VP9 good, cpu-used 3, CRF 38. Archival MP4s remain in the parent workspace's
`gallery/.masters/`, outside the published site. Each clip has an opening poster.

The gallery uses horizontal scroll snapping, arrows, slide selectors, and a
subtle scale transition. Touch/trackpad scrolling and arrow/Home/End keys on the
track work; reduced-motion preferences disable smooth scrolling and transitions.
Compact card footers identify model, effort, and Real world / Simulator. Both
clips show high effort: the real clip's original footer says high, and all 178
assistant entries in new7 report high after a pre-task change from medium.

Players load on demand and use native controls at normal playback rate. Starting
one pauses the other, and changing the selected card pauses the outgoing player.
`public/media/gallery/manifest.json` records master/delivery hashes, file sizes,
durations, and metadata evidence. Use `url()` for every media link so they resolve
beneath `/kinex/` in both local builds and GitHub Pages.

## Deploy

`.github/workflows/deploy.yml` builds on every push to `main` and publishes to GitHub Pages. Before the first deploy, set *Settings → Pages → Source* to
**GitHub Actions**. CI builds for `https://stacx-lab.github.io/kinex/` and stages
`dist/` inside `_site/kinex/` before uploading `_site/`. This organization-site
repository needs that directory so `/kinex/` serves the homepage and `/kinex`
redirects to it. Documentation lives at `/kinex/docs/`. Local builds use the same
origin and base path; override them with `SITE_URL` and `BASE_PATH` for other hosts.
