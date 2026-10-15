# kinex site

Website for [Kinex](https://github.com/stacx-lab/kinex): landing page and docs.
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

This standalone repository uses
`git@github.com:stacx-lab/stacx-lab.github.io.git` as its remote. Run website and
video-production commands from this directory. It contains the website, the
video-generation skill, and the gallery production files; the retired
`kinex-page/` Docusaurus checkout is not required.

Only Astro's `public/` assets and generated pages are published. The video
masters, edit timelines, provenance, and skill stay outside `public/`. Masters
use Git LFS; generated local delivery copies and review images are ignored. Original robot/session input bundles live separately in
`../sources/` (and `../backup/new*` for the older simulation recordings); these are needed to re-render recordings, not to build or serve
the website.

## Layout

```
src/config.ts                 version, tagline, install cmd, repo, nav, doc groups
src/content/docs/*.md         docs (one file = one page; index.md = /docs/)
src/data/hero-terminal.json   landing-page simulator walkthrough
src/components/               Terminal, ArchDiagram, DeviceDiagram, Wordmark, Contributors, Sidebar, Toc, Search…
src/layouts/                  Base, Doc
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
sources: ["docs/commands.md"]   # internal source references at the reviewed `site.sourceRef` commit
---
```

Write plain Markdown starting at `##`. Use `.mdx` when a page needs an imported Astro component, as in `architecture.mdx`.
Link other pages as `/docs/<slug>/`; the base path is added at build time.
The sidebar, prev/next links, one-page view (`/docs/all/`) and search update automatically.

## Release a new version

1. Bump `version` in `src/config.ts` and `package.json`.
2. Update the docs against the intended Kinex source, set `sourceRef` in
   `src/config.ts` to its full commit hash, and keep each page's `sources` list accurate.

The current documentation was reviewed against `../kinex` commit
`afeddc698d14ea9fb5ae0e88f51fecd89000dec4` (2026-10-14), still version 1.0.0.
For the next refresh, compare that commit with the new source revision. The
previous site already covered the October 12 runtime and discovery changes;
this refresh incorporates the subsequent Python control, image-result, Pi SDK,
calibration guidance and licensing updates. Source references remain in page
frontmatter for maintenance and are not displayed in the documentation footer.

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

`src/components/VideoGallery.astro` sits below the hero. The gallery entries are defined
in `src/data/gallery.ts`; media files live in `public/media/gallery/<id>/`.

- `abc-yam-cube`: a 75-second real-world dual-YAM cube solve, with a synchronized
  session replay, device map, and camera observations. Source: `../sources/abc-yam-cube`.
- `teleavatar-tube-transfer`: a 75-second real-world TeleAvatar tube transfer in
  the second slot. Shows mobile manipulation, wrist-camera clearance checks, and
  recovery from guide-rim contact. Visible tether assistance is labeled. Recorded
  model/effort: GPT-6-Astra high. Source: `../demo6-dexteleop`; editable timeline,
  renderer, and validation are in `gallery/teleavatar-tube-transfer/`.
- `go2-trash-clean`: an 89-second real-world Go2 + D1 litter collection task,
  immediately after TeleAvatar. Shows coordinated locomotion/manipulation and
  grasp recovery after a broom moves the paper. Includes the operator inspection
  pause and ends at the second verified deposit; does not claim all trash was cleared.
  Source: `../sources/go2-trash-clean`. Rebuild with
  `python3 gallery/go2-trash-clean/build.py --preview`, then without `--preview`.
  `make_edit.py` regenerates the editable map. After the master render finishes,
  run `python3 gallery/go2-trash-clean/deliver.py` to stage, encode, and validate
  delivery copies, then `python3 gallery/go2-trash-clean/verify.py` for timeline
  and full-decode checks. Requires Pillow and FFmpeg.
- `real-hang-mug`: a 60-second real-world YAM red-cup session in the fourth slot.
  Preserves the failed first hang, recovery and replanning, and the right arm's
  active camera positioning to verify peg support. A fixed crop removes 15% of
  the original left edge and 10% of the right edge, retaining full height and
  scaling uniformly to focus on the work area. Source:
  `../sources/abc-yam-hang-mug-real`. Superseded renders and review caches are
  removed; the current master, edit timeline, and provenance are retained.
  Rebuild with `python3 gallery/real-hang-mug/make_edit.py`, then
  `python3 gallery/real-hang-mug/build.py --preview` and without `--preview`.
  After rendering finishes, run `deliver.py` and `verify.py` in that same folder.
  Requires Pillow and FFmpeg; the clock anchors and uncertainty are in `edit.json`.
- `yam-hang-mug`: the archived 45-second simulation recording/session replay, no longer listed in the homepage gallery.

Delivery MP4s retain 1080p/30 FPS (x264 slow, CRF 28, faststart); WebM fallbacks
use VP9 good, cpu-used 3, CRF 38. Archival MP4s live in this repository's
`gallery/.masters/` through Git LFS, outside the published site. Each clip has an opening poster.

The gallery uses a wider 1440px container, with the video taking roughly three
quarters of the layout on large screens and two thirds on smaller desktops.
It rotates a vertical three-dimensional ring, with neighboring videos tilted above and below the active video. A
fixed edge mask fades the top and bottom; card changes animate rotation. The
right sidebar lists every video title with its robot name. Selecting a title switches
playback and expands only that video's compact embodiment/model/effort/environment
subtitle and highlights. A compact current/total counter sits beneath the playlist;
the sidebar has no arrow buttons or pagination dots.
On narrow screens, the list sits below the videos. Translucent up/down buttons
stack vertically inside the active video's right edge. Neighboring previews, vertical touch swipes, and
Up/Down/Home/End keys on the track work. Reduced-motion preferences disable
the transitions. The cube run records medium effort. Both mug
clips show high effort: the real clip's original footer says high, and all 178
assistant entries in new7 report high after a pre-task change from medium.

Players load on demand. `GalleryPlayer.astro` adds a theme-aware control dock
in a compact single row below the footage with a draggable timeline, hover timestamps, buffered progress,
play/pause, volume, and fullscreen. Playback runs at 1×;
native controls remain available without JavaScript. With the video focused,
Space/K toggles playback, Left/Right seeks five seconds, M mutes, and F opens
fullscreen. Range controls support their native keyboard interactions. Starting
one pauses the other, and changing the selected card pauses the outgoing player.
Dragging player controls does not trigger the gallery's vertical swipe gesture.
Highlight intervals in `src/data/gallery.ts` use delivered-video times from each
clip's provenance. A separate colored strip below the playback progress line matches the sidebar's timestamp
buttons; hovering shows the action title, clicking anywhere on a sidebar highlight
seeks and plays, and playback highlights the matching note. Clip bands use teal,
amber, and blue; the purple playhead keeps a contrasting border in both themes.
Cube and red-cup intervals are selected examples of each capability. The litter
clip marks the disturbance/recovery interval as robustness, the return for the
next piece at 00:50–00:59 as spatial memory, and the rest as locomotion/manipulation.
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
can publish them without an LFS download. Local builds need `git lfs pull` for the ROS 2 video.
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

### Cube video reproduction

`gallery/abc-yam-cube/build.py` adapts the external DJI recording and JSONL export
for the current skill renderer. With Pillow and FFmpeg installed, run:

```sh
python3 gallery/abc-yam-cube/build.py --preview
python3 gallery/abc-yam-cube/build.py
```

The editable `gallery/abc-yam-cube/edit.json` records the 75-second timeline,
reviewed camera-clock offset, source-specific device geometry, and public event
selections. Source time remains continuous from frame zero through the solved
blue-face-up presentation; later table placement is omitted. Every successful
physical command receives a protected motion window (at most 20×, with key turns
and final presentation at 5×). Stationary planning uses smooth speed ramps, and
the final solved view holds for 2.2 seconds. At the user’s request, a status line
below the recording shows `Autonomous`, real recording elapsed / total time
(`HH:MM:SS / HH:MM:SS`), and a brief current action. The total is 01:02:22,
ending at the retained solved presentation; acceleration multipliers and the
bottom-right export timer are omitted. Model and effort appear only in the
video title subtitle. Labels are grounded in the reviewed physical commands
and public task phases in `status_overlay`.
The adapter verifies embedded-image hashes against their original tool results,
keeps hidden thinking out of the replay, and never executes source-session code.
Generated frames and source-image links stay in an ignored `.cache` directory.
The archival render goes to `gallery/.masters/abc-yam-cube.mp4`; delivery files
are encoded separately under `public/media/gallery/abc-yam-cube/`.
