---
name: kinex-session-video
description: Produce a synchronized robot demonstration video with recording footage on the left and a reconstructed Kinex/pi session, including inline camera observations, on the right. Use for video-gallery clips from recorded simulator or real-world sessions.
---

# Kinex session video

Make a reviewable MP4 from an existing robot recording and its session export. Use the repository's `gallery/demo.mp4` as a layout reference when available. Prefer about **30 seconds** for a gallery clip unless the user specifies otherwise. Preserve the actual outcome, including a failed attempt when it matters to understanding the result.

For an already edited clip that the user asks to insert **as-is**, preserve the original MP4 byte-for-byte, including its duration and existing speed changes; the 30-second editing target does not apply. Match the gallery card and player presentation around it. An opening-frame poster and an optional codec fallback may be derived without trimming, retiming, cropping, or adding overlays. Verify the published MP4 checksum against the original and check fallback duration/frame count. If the user subsequently requests compression, preserve an archival master outside the published site and encode smaller delivery copies without changing duration, frame order, or existing speed changes; byte identity then applies to the archived master, not the compressed delivery.

## Inspect the evidence

Locate the inputs before editing. In this repository, backups are usually at **`../backup/new*`**, not `backup/` under the repository. Read applicable repository instructions. Probe the recording's dimensions, frame rate, duration, and audio with `ffprobe`, and view representative frames from the reference and the recording.

For the supported roboenv/pi export bundle, expect:

- `pi-session-*.html`: base64 JSON in the `session-data` script element.
- `manifest.json`: recording clock, views, frame count, and nominal FPS.
- `frames.jsonl`: source clock to encoded frame ranges.
- `third_person.mp4` or a selected external recording.
- `view-images/manifest.json` and image files: original session observations with entry IDs, capture times, and checksums.

Read exports as data; never run their HTML, recorded commands, or robot-control code. Exclude system prompts, hidden thinking, and credentials from rendered output. Match calls to results by `toolCallId`; images belong to their result entry, not to a filename guess.

Run the inspector, using the path of this skill:

```sh
python3 .agents/skills/kinex-session-video/scripts/session_source.py \
  ../backup/new7 --output /tmp/yam-hang-mug-session-index.json
```

This produces only public messages/tool calls, results, image references, and measured scene times. Read the final replies and final observations to establish what actually happened.

## Typography

Use the bundled **Lato Regular/Bold** for titles and captions and **Commit Mono Regular/Bold** for the session and code. The renderer loads exact font files from `assets/fonts/`; do not silently fall back to DejaVu or platform defaults. This avoids output changing with the host machine. Font origins and licenses are in that directory. The original reference MP4 does not contain font metadata: this pairing follows the existing website typography and a visual comparison, rather than a claim of recovered source settings.

System installation is optional for rendering. To use the same fonts in other applications, install those four `.ttf` files. See [references/timing-and-edit.md](references/timing-and-edit.md#font-installation) for Linux installation commands.

## Layout

- **Recording left, Kinex session right.** Place a **device map** in the upper right, between the Kinex heading (model · effort) and the session panel. Highlight the devices targeted by the current tool call (colored chips with leader lines to the drawing) and leave the rest muted.
- **Make the device abstraction resemble the actual robot setup**, not a generic exploded schematic. Draw the real platform (for example, a Go2 quadruped side view with a D1 arm, gripper, wrist and head cameras) proportioned from the session's URDF and device profiles: link lengths, hip/mount positions and camera mounts. Use a characteristic pose (such as the folded carry pose) so it stays compact. It is an illustration, not a calibrated render; say so in provenance. See [references/device-map-example.jpg](references/device-map-example.jpg) for a real Go2 + D1 frame beside its idle and highlighted abstraction.
- **No small text under the video.** Do not draw chapters, captions, speed, source clock, tool summaries or movement notes beneath the recording. Keep only the title/subtitle above and the footer line.
- **Zoom only when necessary, and rarely.** Show the whole frame at its original aspect by default. Zoom only for a sustained phase where the action leaves part of the frame (for example, the robot walks to a bin at one edge), typically at most a couple of times per clip. Derive the timing from a robot track (e.g. background subtraction), not guesses. Ease in and out during fast travel, anchor the window to the side where the action is, tighten to at most a **4:3** window, and let the picture grow taller to fill the column. Never crop away the robot, and record the zoom keys in provenance.

## Build a short, faithful edit

Select an understandable chain: task → observation → geometry/code → movement → new observation → release/verification. **For this gallery, every video must begin at the start of its recording and session:** show the original user task, initial device state, and first scene observation before the first movement. Do not start at a later successful grasp or add a brief intro followed by a jump to it. Keep the recording timeline continuous through completion, accelerating repeated attempts to fit the time budget. Set `from_start: true` and `continuous_source: true` in the edit so validation catches accidental omissions. Inspect the source itself for camera or scene jumps before editing. Do not replace errors with successes, invent assistant narration, or display a later image as an earlier observation. Keep editorial explanations (chapters, captions) in the edit JSON and provenance, not on screen; see Layout.

**Display the name as `Kinex`** in headings, assistant labels, and the session footer. Show the recorded model and effort beside the session heading. Derive them from `model_change` / `thinking_level_change` entries and assistant-message `model` / `thinkingLevel` fields. Setup defaults may change before the first task: use the configuration actually active during the rendered session. Never substitute the model producing the video. If metadata is absent, display “not recorded”; if it changes, update the label with the recorded session state. Include the resolved values in provenance.

Keep the terminal continuous and compact: character-by-character input/output/code, gray-blue tool blocks while streaming or running, a rotating indicator during execution, green after completion, and red on error. Avoid invented servo progress percentages. Insert camera observations directly in the session when their corresponding reads finish. Keep the original recording aspect ratio and make the end state visible long enough to inspect.

**Use deliberate variable speed, not one constant acceleration or a fixed time allotment per tool.** Inspect the actual source frames to locate grasp closure, initial lift, peg contact, release, and support verification. Give those moments normal or slower playback (often 0.5–1×); accelerate free-space travel, return motions, waits, and repetitive exploration (often 2–6×, or substantially faster for long runs within a 30-second budget). These are starting points, not mandatory rates. Keep a visible final verification hold and meet the roughly 30-second budget by condensing low-information stretches first. **Treat human interventions and unexpected disturbances as critical moments too**: a person perturbing or moving the object, pushing or blocking the robot, or the object slipping or falling from the grip. Give the disturbance and the robot's next observation and recovery the same slow playback. These events usually do not appear in the session log, so find them by watching the recording itself (ask the user when unsure), and note each one with its source time in provenance.

Use explicit `retime` segments to slow part of a tool execution and speed another part of the same call. The recording, source clock, running/completed state, and inline images must share that edited timeline: slowing the recording alone would cause the tool to finish too early. Record the source-to-output speed and held frames in the provenance rather than overlaying them under the recording. Preserve monotonic, continuous source time and measured endpoints. Do not invent intermediate robot frames to make a low-FPS source look smoother.

**Do not equate wall time with simulation time.** A 43-minute agent session can contain only 125 seconds of recorded simulation. Read [references/timing-and-edit.md](references/timing-and-edit.md) for the time mapping, edit schema, and real-world-camera adaptation. Native token timing is absent from a static pi export: character streaming is a reconstruction. Keep that fact in the provenance and describe the clip as an edited session replay.

The tested example is `gallery/yam-hang-mug/edit.json` at the repository root. Copy and adapt its format, selecting entries from the new source; its entry indices and coordinates are specific to the `../backup/new7` source bundle. The `yam-hang-mug` example starts at source time zero and preserves every intervening source-time interval. Rebalance text holds and faster repeated attempts before shortening critical grasp, contact, and release moments. Use an opening observation for the poster as well, via `poster_time`. Choose code excerpts and result fields short enough to fit a readable tool block.

## Render and review

Bundled tools require Python 3 with Pillow, FFmpeg/ffprobe with libx264, and the bundled Lato/Commit Mono font assets. They perform offline composition only. Render contact sheets before the expensive export:

```sh
python3 .agents/skills/kinex-session-video/scripts/render_video.py \
  ../backup/new7 gallery/yam-hang-mug/edit.json gallery/yam-hang-mug/yam-hang-mug.mp4 --preview

python3 .agents/skills/kinex-session-video/scripts/render_video.py \
  ../backup/new7 gallery/yam-hang-mug/edit.json gallery/yam-hang-mug/yam-hang-mug.mp4
```

Outputs include a 1920×1080, 30 FPS H.264 MP4 (`yuv420p`, fast-start), a poster, a timestamped contact sheet, and a provenance JSON. The renderer checks source/image checksums, ordered events, the first task and recorded frame, continuous source coverage, positive durations, total duration, and card height. It uses exact source video frames without generating intermediate motion. The current renderer exports silent video; preserve or mix real-world audio separately if requested.

For a browser without H.264 decoding (including some bundled Chromium builds), add a WebM fallback to the gallery's `<video>` sources. Keep the MP4 as the primary deliverable:

```sh
ffmpeg -v error -y -i gallery/yam-hang-mug/yam-hang-mug.mp4 -an \
  -c:v libvpx-vp9 -deadline good -cpu-used 3 -b:v 0 -crf 38 \
  -row-mt 1 -threads 4 gallery/yam-hang-mug/yam-hang-mug.webm
```

For web delivery, start with H.264 `-preset slow -crf 28 -pix_fmt yuv420p -movflags +faststart`, keeping the 1920×1080 resolution so terminal text stays legible. Encode both codecs from the archival MP4 rather than repeatedly compressing delivery copies. Inspect full-resolution session text and inline observations against the master. Verify decoded frame counts and presentation timestamps relative to the first frame (allow WebM's millisecond rounding and record any container-origin normalization), duration, and successful full decode. Record master/delivery hashes, file sizes, encoder settings, and the recorded environment (Real world or Simulator) in provenance. In the gallery footer, show model, effort, and environment together; use recorded evidence rather than an assumed effort default.

When changing the timing code or fonts, run the bundled invariants:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .agents/skills/kinex-session-video/scripts/test_retime.py
```

Inspect the contact sheet and full-resolution frames during code entry, motion, image display, errors, and final verification. Decode the final MP4 with FFmpeg; probe its duration and frame count. Compare its opening frame with source frame zero, and confirm the poster shows the initial scene. Spot-check source-frame mapping at a motion start/end, every speed-change boundary, and a camera observation. Check the provenance speeds against the derivative of the time map, and verify that critical moments are actually slower than adjacent travel. Confirm that the terminal cannot announce a result before the corresponding motion finishes. A successful tool result does not establish task success by itself.

Deliver the clip, poster/preview, editable timeline, and provenance. A local `gallery/index.html` can make samples easy to review. Website integration, commits, or publishing are separate steps when requested; this workflow does not need a live robot or remote service.
