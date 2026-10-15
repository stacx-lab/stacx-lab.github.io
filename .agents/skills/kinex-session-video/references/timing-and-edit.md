# Timing and edit format

## Three clocks

1. **Session wall clock:** entry ISO timestamps. Useful for causal ordering and source duration, not a simulation-video seek time.
2. **Recorded source clock:** `manifest.clock`, `frames.jsonl[].source_time_s`, camera `timestamp`, and world `time_s`. Match clock domains before using these values.
3. **Edited output clock:** cumulative `events[].duration` in the edit JSON.

For the supported simulation bundle, inspect tool-result JSON recursively for measured `timestamp`/`time_s` values. `session_source.clocks()` carries the latest measured source time forward. It intentionally ignores assistant-message millisecond timestamps. For video lookup, find the last `frames.jsonl` row with source time at or before the desired scene time, then use its `frame_start` as the encoded frame index. Do **not** use `source_time_s * fps`: source samples can drift from the nominal frame cadence.

A motion event starts at its latest measured source time and ends at the result's measured time. During reconstructed code entry, hold the source frame. Map source time during execution using the selected speed segments, then hold at the measured endpoint as the result streams. A linear map is only the fallback for events without a speed plan. This is synchronization to measured endpoints, not a recovery of unrecorded per-token/per-servo timestamps. Avoid claiming more precision than the artifacts contain.

Errors may lack a time. Inspect the next device observation. The optional `end_clock_entry` explicitly chooses that measured endpoint; intervening stop calls can use the same `start_clock_entry`/`end_clock_entry` so time does not run backwards. Record this inference, and only use an observation that bounds the same motion. Never stretch one error over unrelated later movements. When several consecutive calls share only one later measurement, `following_calls` can display their original arguments and results together as an ordered sequence. Give each selection its `entry`, optional `call`, and a verbatim `result_text`, and anchor the sequence with `end_clock_entry`. Individual call boundaries remain unknown; preserve that fact in provenance.

For this gallery, begin with the first user task at the first recorded frame and retain continuous source time through the reviewed task-completion endpoint. Later cleanup may be excluded; document the retained endpoint and use it as the displayed total. Set `from_start: true` and `continuous_source: true`; the compiler rejects a late start or a gap. Camera images enter the terminal after their corresponding `read` result. If the raw source itself contains a discontinuity, disclose it rather than disguising it with invented frames.

## Variable speed

Use variable speed to cover the **retained recording from zero through completion**, including earlier attempts, within the requested time budget. About a minute is a starting point for this gallery; allow task complexity and readable movement to inform the edit. Preserve slower grasp closure, peg contact, and release; accelerate repeated exploration more strongly when the recording is long. The `yam-hang-mug` example retains the initial task, joint state, and first camera image, covering roughly 228 source seconds from `../backup/new7`.

Check continuity at every event boundary as well as inside each speed segment. Shortened text excerpts do not require skipping recording time. For fast sequences with missing per-call clocks, group the original calls under the next measured observation; do not invent boundaries or make a failed attempt look successful. Set a `poster_time` during the opening scene observation so the gallery does not visually open on the finished task.

Each speed is **source-clock seconds per output second**, not the acceleration of the agent's wall-clock transcript. For each segment:

```text
output_duration = (source_end - source_start) / speed
whole_event_duration = typing_s + sum(output_duration) + result_hold_s
```

The compiled monotonic map drives the footage lookup, displayed elapsed-time clock and tool-result timing. Use the lower-left multiplier display rule in SKILL.md; annotation filtering must not change this map. Execution remains gray-blue until the entire motion map finishes. Tool results and read images only appear at the corresponding result boundary. The reconstructed text streams during `typing_s`; source footage holds there. Record a held frame as zero speed in provenance, and never record a cut with a finite speed. On screen, freeze the elapsed clock during a hold; sustained holds show 0×.

The map is continuous in position within an event. Segments have constant speed by default. For a gradual speed transition, supply nonnegative `start_speed` and `end_speed` with `speed` equal to their positive arithmetic mean. Speed then varies linearly over output time, and the scene clock integrates that speed exactly. Match adjacent endpoint speeds and use zero next to held frames to avoid abrupt starts and stops. The compiled provenance identifies these segments as `linear_speed`; `speed` is the mean, while `scene_clock()` returns the instantaneous speed. This does not synthesize optical-flow frames or recover original per-token timing. For a 10 FPS source, slow motion repeats available frames; inspect it rather than assuming 30 FPS export creates extra detail.

## Edit JSON

Top-level properties:

| Property | Meaning |
| --- | --- |
| `title`, `subtitle` | Short task title and single metadata subtitle above the footage |
| `robot_label` | Recorded platform name, e.g. `YAM`; builds the subtitle from each event’s recorded model/effort plus environment |
| `status_overlay` | Optional autonomy label and source-interval activity labels; see presentation schema below |
| `recording` | Recording filename within the input bundle |
| `duration` | Required output duration in seconds; sum of event durations |
| `review_times` | Sorted output times for the review contact sheet |
| `events` | Chronological selection of actual session entries |
| `from_start` | Require the first user task at the first recorded source time |
| `continuous_source` | Reject omitted source intervals between events |
| `poster_time` | Output time for the poster; use an opening observation (default 0) |

Each event needs `entry` (zero-based export entry index), positive `duration`, and a short `status_caption` (or `chapter` fallback) for the footer. `caption` may retain a longer editorial explanation in the edit. These descriptions are not fabricated assistant messages.

Tool events are the default. Optional selectors:

- `call`: zero-based tool-call index inside the assistant entry, when it contains multiple calls.
- `code_field`: dot path into the actual arguments, e.g. `command` or `control.python`.
- `code_lines`: one-based lines of that source string. These are verbatim **excerpts**, not a runnable replacement program. Omitted lines stay in the original arguments in the provenance.
- `code_excerpt`: optional verbatim substring of `code_field`, useful for compact sequences; checked against the original code.
- `arg_fields`: selected argument dot paths instead of the full argument dictionary.
- `result_fields`: dot paths into the parsed JSON result, such as `last.gripper.aperture_m`; numeric list indices are supported.
- `result_text`: a verbatim substring of a textual result; checked against the source.
- `start_clock_entry`, `end_clock_entry`: explicitly reviewed measured-clock anchors; see above.
- `following_calls`: additional ordered tool calls sharing a measured endpoint, with optional `code_field`/`code_excerpt` and a verbatim `result_text`; see the clock discussion above.
- `retime`: optional explicit execution-speed plan, documented below; overrides the fraction-based timings.
- `typing_fraction`: portion of the event spent revealing its input/code (default 0.25).
- `result_fraction`: point at which execution finishes and the result begins (default 0.76). Keep `0 < typing_fraction < result_fraction < 1`.

Example `retime` for a release beginning at source time `113.424 s` and ending at `117.062 s`:

```json
{
  "typing_s": 0.35,
  "result_hold_s": 0.35,
  "segments": [
    {"end_source_s": 114.138, "speed": 0.65, "reason": "Show gripper opening"},
    {"end_source_s": "end", "speed": 3.0, "reason": "Accelerate withdrawal"}
  ]
}
```

`"end"` uses the actual measured tool endpoint. Segment end times must strictly increase, cover the entire motion, and stay inside its measured interval. Speeds must be positive. Set the event's `duration` to the computed total (about 2.773128 s here, using the unrounded measured timestamps). The compiler rejects a speed plan that does not fit, rather than silently renormalizing all the speeds. The provenance contains compiled `motion_keyframes` and `speed_segments` with reasons, so another editor can review the pacing.

For public message events, use `kind: "user"` or `kind: "assistant"`; `text` can select a verbatim substring. The renderer verifies it belongs to the source message. Otherwise the complete public text is used. Images are looked up automatically from the chosen tool result, verified against their SHA-256, and scaled for display without altering the originals.

`gallery/yam-hang-mug/edit.json` is the measured-clock simulator example. Its 45-second timeline retains initial observation, geometry, earlier attempts, grasping, release, withdrawal, and final evidence. Its existing exported media predates the current visual defaults: do not copy the old speed counter or blank lower-left footer. The shared renderer supplies the status layout and width check; use `gallery/teleavatar-tube-transfer/build.py` for the current font sizes and filtered integer multiplier annotation. Never copy source-specific entry indices into another session.

## Presentation schema

```json
{
  "title": "Solving a 2x2 cube",
  "robot_label": "YAM",
  "subtitle": "YAM × GPT-6-Astra · medium · Real world",
  "environment": "Real world",
  "status_overlay": {
    "autonomy": "Autonomous",
    "activity": [
      {"start_source_s": 0, "end_source_s": 12, "text": "Reading the task"},
      {"start_source_s": 12, "end_source_s": 30, "text": "Inspecting the scene"}
    ]
  }
}
```

These intervals illustrate the schema, not reusable timestamps. Cover the actual retained source range with reviewed labels. In the generic renderer, `status_caption` on the current event is used if no interval list is supplied, with `chapter` as a fallback. Keep event-level `autonomy` labels consistent with the status rule in SKILL.md. An external adapter can override `Renderer.status(t)` for a global source map and hold-specific descriptions; the shared `draw_status()` handles typography and width validation.

The current status style and content order are defined in SKILL.md. `elapsed_label()` floors source seconds and formats hours explicitly. The generic renderer subtracts the first event’s source origin and uses the last retained event endpoint as total. The external cube adapter uses its normalized recording clock and `end_source_s`. Do not substitute output seconds or the duration of discarded cleanup. Source time must agree with the footage on every frame and remain frozen during editorial holds.

With `robot_label`, the renderer builds the subtitle from the active event’s recorded metadata, updating it if model/effort changes. Otherwise the authored `subtitle` is used; ensure it contains the evidence-derived robot/model/effort. The model appears nowhere else in the video chrome. Source messages and provenance remain intact. There is no bottom-right output clock.

## Long-run pacing example

The final `abc-yam-cube` edit covers source 0–3742.28 seconds in 75 output seconds. It protects 58 successful physical-command windows, including 0.9-second alignment guards, rather than slowing only four layer turns. In this edit, other motions run at no more than 20× with at least 0.4 output seconds each, key quarter turns and final presentation at 5×, and initial lift/verification slower. Stationary planning absorbs the strongest compression. Linear speed ramps join movement and holds continuously.

Those numbers are an accepted example, not defaults for a different robot or task. Inspect actual movement at presentation size. Stop on the clearly solved blue-face-up presentation and hold for 2.2 output seconds; the later table placement moves the cube out of view and is excluded. The final clock reads `01:02:22 / 01:02:22`.

## External real-world recordings

Use the same layout and evidence rules, with the actual camera recording on the left. First establish how the camera clock relates to the session/device clock. Use shared acquisition timestamps, a recorded synchronization marker, or several clearly identifiable movements. For a constant offset, two anchors check the offset; for drift, use multiple anchors and a reviewed piecewise mapping. Keep anchors and uncertainty in provenance.

The bundled adapter specifically expects a roboenv recording manifest, frame map, and extracted pi-image manifest. It is **not** an automatic synchronizer for an arbitrary external MP4. For different inputs, add a small source adapter or produce an explicit frame map in the same schema from validated clock anchors. If device times are epoch timestamps, normalize them and the external camera times to the same origin before applying the mapper. Do not feed wall-clock seconds directly to a simulation mapping, and do not infer synchronization solely from equal video/session durations.

Preserve the original input bundle and store any derived mapping separately. For different aspect ratios, the renderer letterboxes the footage rather than stretching or cropping away robot motion. Do not use wrist footage as a spectator view without identifying that viewpoint.

### Cube JSONL/camera adapter

`gallery/abc-yam-cube/build.py` handles the external DJI MP4 plus original `session.jsonl` and `image-inventory.json`. It shares the bundled renderer’s fonts, device map, session cards, and status-line drawing. Its top-level `retime` is a **global** map, unlike the simulator’s event-local plans:

- `end_source_s`: reviewed retained end, distinct from `clock.last_frame_s` (the full recording’s last frame).
- `retime[]`: `end_source_s` plus either `hold_s`, or `speed` and optional `end_speed`. Here `speed` is the **starting** speed. Segment duration is `2 * source_delta / (speed + end_speed)`. In event-local simulator plans, `speed` remains the **mean**, with explicit `start_speed` and `end_speed`; do not interchange the schemas.
- `clock`: alignment origin, original FPS/frame count, anchors and uncertainty. Use original entry ISO timestamps for call submission/result completion; assistant `message.timestamp` may instead mark generation start.
- `status_overlay.activity`: source-time action intervals, independent of which terminal calls are selected. `hold_labels` maps explicit hold reasons to short summaries. `elapsed_time` documents the displayed total and source domain.
- `source_review.critical_moments`: reviewed physical windows and pacing decisions. Initial/ending source samples alone cannot find all movements or human interventions.

The adapter extracts exact original frames into an ignored cache before composing. Change layout or captions without decoding the entire long source again. Preserve image-to-result hashes, update provenance on rerender, and finish the master before launching delivery encoders. Do not execute the source workspace’s scripts.

## Font installation

Rendering uses exact bundled files and needs no system installation. To install the same families for other Linux applications, from the repository root:

```sh
mkdir -p "$HOME/.local/share/fonts/kinex-video"
cp .agents/skills/kinex-session-video/assets/fonts/*.ttf \
  "$HOME/.local/share/fonts/kinex-video/"
fc-cache -f
fc-match Lato
fc-match "Commit Mono"
```

Install Lato Regular (400), Lato Bold (700), Commit Mono Regular (400), and Commit Mono Bold (700). Restart applications after installation. For macOS/Windows, install the four TTF files with the system font manager. Official distributions are [Lato](https://www.latofonts.com/download/) and [Commit Mono](https://commitmono.com/). Roboto Slab is used by the website's headings but is not needed for this sans-serif video layout.
