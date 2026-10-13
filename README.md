# kinex site

Website for [Kinex](https://github.com/stacx-lab/kinex): landing page, docs, blog.
Astro (static) + Pagefind. No UI framework.
Fonts: Roboto Slab (headings), Lato (body), Commit Mono (code); self-hosted via `@fontsource`, declared in `src/components/Fonts.astro`.

```sh
npm ci
npm run dev        # http://localhost:4321/kinex/  (search needs a build)
npm run build      # dist/ + pagefind index
npm run preview
npm run check      # astro check + build + internal link/anchor check
```

## Repository and workspace

This standalone repository lives at `harness/kinex-doc/` and uses
`git@github.com:stacx-lab/stacx-lab.github.io.git` as its remote. Run website and
video-production commands from this directory. It contains the website, the
video-generation skill, and the gallery production files; the retired
`kinex-page/` Docusaurus checkout is not required.

Only Astro's `public/` assets and generated pages are published. The video
masters, edit timelines, provenance, and skill stay outside `public/`. Masters
use Git LFS; generated local delivery copies and review images are ignored. Original robot/session input bundles live separately in
`../backup/new*`; these are needed to re-render recordings, not to build or serve
the website.

## Layout

```
src/config.ts                 version, tagline, install cmd, repo, nav, doc groups
src/content/docs/*.md         docs (one file = one page; index.md = /docs/)
src/content/blog/*.md         blog posts
src/data/hero-terminal.json   landing-page simulator walkthrough
src/components/               Terminal, ArchDiagram, DemoBanner, Sidebar, Toc, Search…
src/layouts/                  Base, Doc, Post
src/styles/                   global.css (tokens, light/dark), prose.css (markdown)
public/media/                 published camera observations and delivery videos
.agents/skills/kinex-session-video/  video-generation skill, scripts, fonts, references
gallery/.masters/             original archival MP4s (Git LFS; not published)
gallery/<id>/                 tracked edit timeline/provenance; ignored render outputs
gallery/index.html            local review page using public/media/gallery/ assets
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

`Terminal.astro` replays setup and a 30-second mug-hanging walkthrough in an enlarged
terminal with internal scrolling (480px tall on desktop, 420px on mobile). Its
background and tool colors adapt to light/dark mode. Input, assistant replies, tool arguments, code,
and results appear one character at a time. Tool blocks use gray-blue while
streaming or executing, green on completion, and red on error. Running tools show only an indeterminate spinner; servo waits are brief.
Pause/replay, reduced-motion, and no-JavaScript transcript fallbacks are supported.

All seven camera frames come unchanged from one successful session in
`../backup/new5/view-images/`: overhead, right wrist, left wrist, insertion inspection,
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
use VP9 good, cpu-used 3, CRF 38. Archival MP4s live in this repository's
`gallery/.masters/` through Git LFS, outside the published site. Each clip has an opening poster.

The gallery rotates a three-dimensional ring, with the active video centered and
neighbors facing outward at −45°/+45°. A fixed edge mask fades the sides; card
changes animate rotation rather than opacity. Arrows, slide selectors, side-card
clicks, touch swipes, and arrow/Home/End keys on the track work. Reduced-motion
preferences disable the rotation transition.
Compact card footers identify model, effort, and Real world / Simulator. Both
clips show high effort: the real clip's original footer says high, and all 178
assistant entries in new7 report high after a pre-task change from medium.

Players load on demand and use native controls at normal playback rate. Starting
one pauses the other, and changing the selected card pauses the outgoing player.
`public/media/gallery/manifest.json` records master/delivery hashes, file sizes,
durations, and metadata evidence. Use `url()` for every media link so they resolve
beneath `/kinex/` in both local builds and GitHub Pages.

## Video-production skill

Read [.agents/skills/kinex-session-video/SKILL.md](.agents/skills/kinex-session-video/SKILL.md)
for input inspection, editing, rendering, and review. The skill includes its
Python scripts, Lato/Commit Mono fonts and licenses, and timing reference.
Rendering requires Python 3 with Pillow and FFmpeg/ffprobe. Its existing timing
checks can run without the original recordings:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .agents/skills/kinex-session-video/scripts/test_retime.py
```

Use `gallery/yam-hang-mug/edit.json` as the editable example and
`gallery/.masters/real-hang-mug.mp4` as an existing layout reference. Preserve
master files when generating compressed copies for `public/media/gallery/`.

To download the archival masters after cloning, install Git LFS, then run:

```sh
git lfs install --local
git lfs pull
```

Only `gallery/.masters/*.mp4` uses LFS. The compressed MP4/WebM files under
`public/media/gallery/` remain ordinary Git assets so the existing Pages workflow
can publish them without an LFS download. Website builds do not need the masters.
Generated media under `gallery/<id>/` stays local; commit edits and provenance,
then copy reviewed delivery files into `public/media/gallery/<id>/`. The local
`gallery/index.html` review page references those published copies directly.

## Deploy

`.github/workflows/deploy.yml` builds on every push to `main` and publishes to GitHub Pages. Before the first deploy, set *Settings → Pages → Source* to
**GitHub Actions**. CI builds for `https://stacx-lab.github.io/kinex/` and stages
`dist/` inside `_site/kinex/` before uploading `_site/`. This organization-site
repository needs that directory so `/kinex/` serves the homepage and `/kinex`
redirects to it. Documentation lives at `/kinex/docs/`. Local builds use the same
origin and base path; override them with `SITE_URL` and `BASE_PATH` for other hosts.
