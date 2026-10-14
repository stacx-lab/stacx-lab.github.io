# Timing and edit format

## Three clocks

1. **Session wall clock:** entry ISO timestamps. Useful for causal ordering and source duration, not a simulation-video seek time.
2. **Recorded source clock:** `manifest.clock`, `frames.jsonl[].source_time_s`, camera `timestamp`, and world `time_s`. Match clock domains before using these values.
3. **Edited output clock:** cumulative `events[].duration` in the edit JSON.

For the supported simulation bundle, inspect tool-result JSON recursively for measured `timestamp`/`time_s` values. `session_source.clocks()` carries the latest measured source time forward. It intentionally ignores assistant-message millisecond timestamps. For video lookup, find the last `frames.jsonl` row with source time at or before the desired scene time, then use its `frame_start` as the encoded frame index. Do **not** use `source_time_s * fps`: source samples can drift from the nominal frame cadence.

A motion event starts at its latest measured source time and ends at the result's measured time. During reconstructed code entry, hold the source frame. Map source time during execution using the selected speed segments, then hold at the measured endpoint as the result streams. A linear map is only the fallback for events without a speed plan. This is synchronization to measured endpoints, not a recovery of unrecorded per-token/per-servo timestamps. Avoid claiming more precision than the artifacts contain.

Errors may lack a time. Inspect the next device observation. The optional `end_clock_entry` explicitly chooses that measured endpoint; intervening stop calls can use the same `start_clock_entry`/`end_clock_entry` so time does not run backwards. Record this inference, and only use an observation that bounds the same motion. Never stretch one error over unrelated later movements. When several consecutive calls share only one later measurement, `following_calls` can display their original arguments and results together as an ordered sequence. Give each selection its `entry`, optional `call`, and a verbatim `result_text`, and anchor the sequence with `end_clock_entry`. Individual call boundaries remain unknown; preserve that fact in provenance.

For this gallery, begin with the first user task at the first recorded frame and retain continuous source time through completion. Set `from_start: true` and `continuous_source: true`; the compiler rejects a late start or a gap. Camera images enter the terminal after their corresponding `read` result. If the raw source itself contains a discontinuity, disclose it rather than disguising it with invented frames.

## Variable speed

Use variable speed to cover the **entire recording from zero**, including earlier attempts, in the 30-second gallery budget. Preserve slower grasp closure, peg contact, and release; accelerate repeated exploration more strongly when the recording is long. The `yam-hang-mug` example retains the initial task, joint state, and first camera image, covering roughly 228 source seconds from `../backup/new7`.

Check continuity at every event boundary as well as inside each speed segment. Shortened text excerpts do not require skipping recording time. For fast sequences with missing per-call clocks, group the original calls under the next measured observation; do not invent boundaries or make a failed attempt look successful. Set a `poster_time` during the opening scene observation so the gallery does not visually open on the finished task.

Each speed is **source-clock seconds per output second**, not the acceleration of the agent's wall-clock transcript. For each segment:

```text
output_duration = (source_end - source_start) / speed
whole_event_duration = typing_s + sum(output_duration) + result_hold_s
```

The compiled monotonic map drives the footage lookup, displayed scene clock, speed indicator, and tool result timing. Execution remains gray-blue until the entire motion map finishes. Tool results and read images only appear at the corresponding result boundary. The reconstructed text streams during `typing_s`; source footage holds there. Record a held frame as held, not “1×”, and never record a cut with a finite speed; these values live in provenance, not under the video.

The map is continuous in position within an event and piecewise constant in speed. It does not synthesize optical-flow frames or recover original per-token timing. For a 10 FPS source, slow motion repeats available frames; inspect it rather than assuming 30 FPS export creates extra detail.

## Edit JSON

Top-level properties:

| Property | Meaning |
| --- | --- |
| `title`, `subtitle` | Editorial title above the footage |
| `session_label` | Small label beneath the terminal |
| `recording` | Recording filename within the input bundle |
| `duration` | Required output duration in seconds; sum of event durations |
| `review_times` | Sorted output times for the review contact sheet |
| `events` | Chronological selection of actual session entries |
| `from_start` | Require the first user task at the first recorded source time |
| `continuous_source` | Reject omitted source intervals between events |
| `poster_time` | Output time for the poster; use an opening observation (default 0) |

Each event needs `entry` (zero-based export entry index), positive `duration`, `chapter`, and `caption`. Captions are editorial and can summarize the action; they are not fabricated assistant messages.

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

`gallery/yam-hang-mug/edit.json` is a 30-second example starting at source time zero. It retains the first task and observation, measured geometry, earlier attempts, grasping, release, withdrawal, and final camera evidence. Memo editing is omitted from the presentation, but intervening recording time is retained. Do not reuse source-specific entry indices for another session.

## External real-world recordings

Use the same layout and evidence rules, with the actual camera recording on the left. First establish how the camera clock relates to the session/device clock. Use shared acquisition timestamps, a recorded synchronization marker, or several clearly identifiable movements. For a constant offset, two anchors check the offset; for drift, use multiple anchors and a reviewed piecewise mapping. Keep anchors and uncertainty in provenance.

The bundled adapter specifically expects a roboenv recording manifest, frame map, and extracted pi-image manifest. It is **not** an automatic synchronizer for an arbitrary external MP4. For different inputs, add a small source adapter or produce an explicit frame map in the same schema from validated clock anchors. If device times are epoch timestamps, normalize them and the external camera times to the same origin before applying the mapper. Do not feed wall-clock seconds directly to a simulation mapping, and do not infer synchronization solely from equal video/session durations.

Preserve the original input bundle and store any derived mapping separately. For different aspect ratios, the renderer letterboxes the footage rather than stretching or cropping away robot motion. Do not use wrist footage as a spectator view without identifying that viewpoint.

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
