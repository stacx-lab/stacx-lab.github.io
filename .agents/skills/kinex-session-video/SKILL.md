---
name: kinex-session-video
description: Create or revise synchronized robot demonstration videos with recording footage, a reconstructed Kinex/pi session, inline camera observations, and gallery-ready delivery assets.
---

# Kinex session video

Produce an evidence-linked robot demo with **recording left, Kinex session right**. For this repository’s gallery, use the final cube video as the presentation reference: [layout example](references/gallery-layout-example.jpg), `gallery/abc-yam-cube/edit.json`, and its external-camera adapter `build.py`. The defaults below reflect the user’s final layout; a later user instruction takes precedence.

Aim for about a minute when no duration is specified. Preserve readable motion and recovery rather than forcing every task into the same length. The cube’s 75-second edit is an example for a long recording, not a universal duration.

For an edited clip requested **as-is**, preserve its original MP4 byte-for-byte, including duration and speed changes. An opening poster or codec fallback may be derived without recutting or adding overlays. If the user requests compression, keep an archival master outside the published site and encode delivery copies without changing frame order or timing.

## Inputs and evidence

New recordings in this repository are generally in **`../sources/<task>`**; older simulator bundles are in **`../backup/new*`**. Honor the supplied path. Inspect manifests and filenames before reading large exports. Never execute exported HTML, recorded commands, or robot-control code.

For the bundled roboenv/pi format, use:

```sh
python3 .agents/skills/kinex-session-video/scripts/session_source.py \
  ../backup/new7 --output /tmp/session-index.json
```

That format contains `pi-session-*.html`, a recording manifest, `frames.jsonl`, a spectator video, and extracted camera observations. External recordings may instead contain an MP4 and `session.jsonl`; use a source-specific adapter. Read [timing-and-edit.md](references/timing-and-edit.md) for clock mapping, schemas, and the cube adapter’s differences.

Probe the video, inspect initial and final observations, and review source frames across the run. Keep public messages and verbatim tool excerpts; exclude system prompts, hidden thinking, and credentials. Match calls and results by `toolCallId`, and verify embedded image hashes. Derive model and effort from the configuration active during the task and assistant-message fields, not setup defaults or the model making the edit. Preserve unknown metadata as unknown.

## Final gallery layout

Use exact bundled **Lato Regular/Bold** and **Commit Mono Regular/Bold**. Do not silently substitute system fonts.

- **Short task title above the recording.** Keep the robot/model out of the title: `Solving a 2x2 cube`, not a long title that wraps in the homepage sidebar.
- **One metadata subtitle:** `YAM × GPT-6-Astra · medium · Real world`. Use the actual robot, recorded model/effort, and environment. Put model information here once; omit duplicate model/effort text beside the Kinex heading and beneath the session.
- **Kinex heading and device map at upper right.** Keep the map above the scrolling session. Match the actual robot setup using device profiles, URDF dimensions and camera mounts. Highlight exact device IDs from the active call. The illustration is not live or calibrated kinematics; state that in provenance. See the [device-map example](references/device-map-example.jpg) when adapting another platform.
- **Lower-left status:** Outside the recording, use one line of Lato 24 px text and a Commit Mono 22 px clock on the 1005 px baseline at 1080p, ordered `Autonomous 10× | elapsed / retained total | short action`, with subtle separators and integer-rounded multipliers that retain the previous stable value through changes shorter than 0.35 s, without altering actual video speed.
- **Real elapsed / retained total time, not output time.** For a real recording, show the same original source clock used by the footage, normalized to its beginning, in `HH:MM:SS / HH:MM:SS`. The total ends at the selected task-completion endpoint; excluded cleanup is not counted. Holds freeze the elapsed clock. For simulation, use the measured simulation clock and identify the environment; do not call it real wall time. If actual wall time is requested, establish that separate mapping first.
- **No bottom-right export counter.** Exact speeds remain in provenance.

The action is an editorial summary grounded in public commands and reviewed motion, such as `Inspecting cube faces`, `Planning the solution`, `Handing off the cube`, or `Solved — blue face up`. Update it with the source timeline, including omitted terminal calls; a selected terminal card may remain visible across several physical actions. Do not invent assistant narration. Keep the status label `Autonomous` throughout, as requested; retain observed human interventions in source-review records.

Preserve the recording’s original aspect ratio. Zoom only when necessary to keep an action visible, rarely, and with reviewed eased transitions. Never crop away the object or robot. Keep inline camera observations attached to their actual tool results, gray-blue running cards, green completed cards, and red errors. Character streaming is reconstructed, not recovered token timing.

## Pacing and ending

Begin at the first recorded frame with the original task, initial state, and first observation. Set `from_start: true` and `continuous_source: true`; keep source time continuous through the selected outcome. Do not use an opening intro followed by a jump to the successful attempt.

**Protect every physical motion, not only a few key turns.** Mark camera repositioning, approaches, grasps, handoffs, reorientation, and withdrawal as well as task-critical contact. Review the footage to catch motion or human disturbances absent from the log. Aggressively condense stationary planning first. Applying a very high background speed to unmarked movements produces apparent jump cuts, even when the mathematical source map is continuous.

Give task-critical turns, contact, failures, recovery, and verification more time. Ease speed changes while preserving a monotonic source map shared by the footage, tool completion, images, and status clock. Do not fabricate optical-flow frames. Review transitions at playback scale; a 30 FPS export alone does not guarantee readable movement.

**End on a clear completed state and hold it briefly.** Omit later placement, cleanup, or extra checks when they add no task evidence or move the object out of frame. Preserve failures that explain the outcome. Do not infer success from a successful tool call alone. For the cube, the chosen end is the solved blue face up, before the later placement leaves the camera view. Its retained real duration is 01:02:22, with a 2.2-second output hold.

## Render, review, and deliver

For a simulator bundle, use the bundled renderer after authoring the source-specific edit:

```sh
python3 .agents/skills/kinex-session-video/scripts/render_video.py \
  ../backup/new7 gallery/yam-hang-mug/edit.json gallery/yam-hang-mug/yam-hang-mug.mp4 --preview
```

For the external cube bundle, use its adapter:

```sh
python3 gallery/abc-yam-cube/build.py --preview
python3 gallery/abc-yam-cube/build.py
```

Render preview frames before the full export. Inspect opening, motion, error/recovery, observation, and ending frames at full resolution. Check status text width, actual source-time progression, and the absence of duplicate metadata/output counters. The renderer formats the final status line by default; see the reference for `robot_label`, `status_caption`, and interval-based activity labels.

Keep the archival master under `gallery/.masters/` and delivery files under `public/media/gallery/<id>/`. Start with H.264 `-preset slow -crf 28 -pix_fmt yuv420p -movflags +faststart` and VP9 `-crf 38 -b:v 0 -row-mt 1`, both 1080p30, encoded from the master. The current workflow exports silent video; preserve original audio in the source unless requested otherwise.

**Finish rendering before delivery encoding reads the master.** A new render can invalidate an in-progress MP4 read. Encode delivery copies into a staging directory, then replace the website files after encoding succeeds. Preserve originals and update the poster, checksums, frame counts, duration, and provenance together.

Validate full decode, frame count and timestamps for both codecs. Check opening frame zero, monotonic source mapping, tool-result/image timing, critical-motion pacing, and elapsed-clock correctness including holds. WebM timestamps may round to milliseconds. When timing or shared rendering code changes, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .agents/skills/kinex-session-video/scripts/test_retime.py
```

Retain the editable timeline, source-clock anchors/uncertainty, reviewed motion windows, source-frame mapping, recorded metadata, font hashes, encoder settings, and final file hashes. For this cube adapter, `verify.py` checks the timeline, every displayed elapsed-time label, and full delivery decode.

## Homepage integration

When requested, keep the gallery’s vertical rotation, video column at roughly two thirds and explanation column at one third, stacking on mobile. Keep the task title short; show `robot × model · effort` beneath it and the real/simulated environment nearby.

Make demonstrated capabilities scannable with bold short labels and one concrete sentence each. For the cube: **Active sensing** (wrist-camera views of all faces), **Solution reasoning** (state reconstruction and solving sequence), and **Precision & collision avoidance** (layer turns and handoffs around arms, grippers, and cameras). For the red cup: highlight recovery after the first failed hang and the other arm’s active camera positioning. Use task-specific evidence, not generic praise.

Update gallery data, media paths, poster, and manifest, then run the site checks and rebuild after the final media replacement. Committing or publishing still requires the user’s request.
