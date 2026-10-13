---
title: Recording
description: Record what your robot sees and does, understand the files you get, and use recordings for self-improvement and training data.
group: Guides
order: 60
sources: ["docs/commands.md", "docs/agent-integration.md", "packages/core/src/commands.ts", "packages/core/src/tool/record.txt", "packages/core/src/record/layout.ts", "packages/core/src/config/config.ts"]
---

A recording captures what your devices observed and what they were commanded to do while Kinex works on a task, together with the conversation that drove it. Use it to review a run, compare trials, or collect demonstrations.

## How to record

### From the TUI

Load the devices first (`/load arm`); unloaded devices are refused. Then start a recording with the devices you want and how often to sample each one (in Hz). Anything after the rates is the task instruction:

```text
/record start arm=10 gripper=10 wrist_cam=5 pick up the red mug and place it in the bin
```

Then let Kinex work, or steer it yourself. The recording keeps running across turns and while the agent is thinking. Along the way:

```text
/record snap wrist_cam grasp attempt     # mark a moment and save a full-quality image
/record status                           # check rates, frame counts and any problems
```

When the task is done, stop and label how it went (`success`, `failure` or `partial`), with an optional note:

```text
/record stop success Mug placed in the bin on the first try
```

The device list and rates are fixed once a recording starts. To change them, stop and start a new one.

### In scripted runs

Pass the devices and rates to a headless run; the recording covers the whole task:

```sh
kinex -p --record "arm=10 gripper=10 wrist_cam=5" "Pick up the red mug and place it in the bin"
```

### Letting the agent record

Start Kinex with `--enable-recording` to give the agent the `record` tool. It can then start, snap and stop recordings itself, for example to capture each attempt in a series of trials.

Camera recording needs `ffmpeg` on your `PATH`.

## What you get

Each recording is a folder under `.kinex/recordings/`:

```text
.kinex/recordings/rec_00mv475jct0000ur/
├── recording.json          # summary: task, devices, rates, counts, outcome
├── timeline.jsonl          # what happened when: start, tool calls, notes (including snaps), stop
├── trace.json              # the conversation: messages and tool calls (no image data)
├── profile/                # device profiles and workspace.yaml as they were at the start
├── devices/
│   ├── wrist_cam/
│   │   ├── stream/
│   │   │   ├── video.mp4   # the camera stream
│   │   │   ├── depth.mkv   # lossless depth, for RGB-D cameras
│   │   │   └── frames.jsonl  # timestamp of every video frame
│   │   ├── frames/         # full-quality images from /record snap
│   │   └── events.jsonl    # every call made to this device
│   └── arm/
│       ├── stream/state.jsonl  # sampled joint state
│       └── events.jsonl        # every call, including the commands sent
└── passive/                # other devices the agent used but you didn't list
```

The main files:

| File | Contains |
| --- | --- |
| `stream/video.mp4`, `depth.mkv` | What each camera saw, as video |
| `stream/frames.jsonl` | When each video frame was captured, so video can be lined up with other data |
| `stream/state.jsonl` | Sampled device state, such as joint positions and velocities |
| `events.jsonl` | Every call to the device: reads, and writes with the full commanded actions |
| `timeline.jsonl` | Session events in order: start, tool calls, notes (including snaps), stop |
| `trace.json` | The conversation that produced the run |
| `profile/` | The calibration and frame setup the run used |
| `recording.json` | The summary, including the instruction, outcome label and capture statistics |

Some sample lines, from an arm's state stream and a command sent to it:

```json
{"positions": [-0.207, 0.473, 0.994, -0.704, -0.308, -0.329], "velocities": [0, 0, 0, 0, 0, 0], "timestamp": 0, "t_ns": 1791267198127000000}
{"t": 649, "seq": 4, "action": "write", "args": {"actions": [[-0.207, 0.473, 0.994, -0.704, -0.308, -0.329], ...], "duration_s": 0.5}}
```

Every stream carries timestamps, so cameras, joint states and commands can be aligned afterwards even though they were sampled at different rates.

### Checking quality

`recording.json` reports, per device, how many samples were taken, the rate actually achieved (`effectiveHz`), missed capture slots (`skipped`) and read errors. Video plays at a fixed frame rate; when a camera can't keep up, the last image is repeated so elapsed time stays correct, and `repeated` counts those frames. Check these before relying on a recording. A device that fails doesn't stop the others.

Recordings end when you stop them, when the size limit is reached, when you start a new session, or when you change workspace. Unloading a device ends its part of the recording.

## Using recordings

Each recording keeps the instruction, the outcome, the conversation and the exact device data, which makes it useful beyond review:

- **Refining skills and tools.** Point the agent at past recordings, for example "review the last three failed runs and update the pick-and-place skill". It can compare failed and successful attempts and turn what it finds into better skills, tools or parameters.
- **Training models.** Observations, commanded actions and outcome labels are already in the shape of robot-learning episodes, so recordings can be turned into training data for policies that then run through [`run_policy`](/docs/vla/).

To save just the conversation, use `/export` instead; see [Working with the agent](/docs/agent/#exporting-a-conversation).
