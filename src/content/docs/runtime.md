---
title: Kinex runtime
description: What the runtime does between the agent and your robot — devices, discovery, permissions, frames, time, Python and context.
group: Concepts
order: 40
label: Runtime
sources: ["packages/core/README.md", "docs/overview.md", "docs/agent-integration.md", "docs/devices.md", "packages/core/assets/builtin/tool/relative-pose/tool.yaml", "packages/core/src/permission/index.ts", "packages/setup/src/index.ts"]
---

The Kinex runtime (`@kinex/core`) sits between the agent and the robot. Every robotics tool call the agent makes, and every device command you type (`/load`, `/stop`, `/record`…), passes through it. The runtime holds no model, conversation or UI; those come from the host (standalone Kinex, or a [plugin for another harness](/docs/plugins/#using-kinex-from-other-harnesses)). What it does provide is everything needed to use devices safely and consistently.

## Device management

Each device runs on its own. Its driver is a separate process with its own resources, such as an SDK connection, a camera stream or a model loaded on a GPU, so one device failing or hanging doesn't take down the others.

- **Loading in parallel.** `/load all` starts every driver at once and waits for each independently, so a slow model server doesn't hold up the arm.
- **Scheduling per device.** Writes to one device run one at a time, in order. Reads can run alongside writes, and different devices work concurrently. `devices` uses this to read a camera and an arm in one call.
- **Clean release.** `/unload`, quitting or switching workspace shuts down the processes Kinex started. Services it only connected to, like a simulator you launched yourself, are left running.
- **Surviving session changes.** Starting a new conversation or resuming an old one in the same workspace keeps devices connected. In-flight calls are cancelled, session approvals are reset and any active recording ends.
- **No silent restarts.** If a driver fails, it stays failed until you reload it with `/unload` and `/load`.

See [Devices](/docs/devices/) for types, profiles and drivers.

## Tool and skill discovery

The runtime rescans tools and skills on every agent step. Drop a new Python tool into `.kinex/tools/` or a new `SKILL.md` into `.kinex/skills/`, and the agent can use it at the next step, without restarting Kinex. The agent can do the same: it can write itself a tool mid-task and then call it. Project, global and built-in locations are searched in a fixed order, so a project can override a shared tool or skill. See [Tools & skills](/docs/tools-and-skills/#discovery).

## Permissions

Every tool call the agent makes is checked before it runs. Your own slash commands, like `/load` or `/record`, are trusted and never checked. How often you're asked depends on the [approval mode](/docs/agent/#approval-modes); in the default `ask` mode, Kinex follows these permissions:

| Permission | Covers | Default |
| --- | --- | --- |
| `device_read` | Reading devices and running model inference | ask |
| `device_act` | Moving actuators, waiting on the world clock, loading and unloading through the `device` tool | ask |
| `device_stop` | Stopping devices | always allowed |
| `python_tool_controller` | `exec` scripts, and Python tools that command devices | ask |
| `python_tool` | Python tools that only read | ask |
| `record` | The agent starting or stopping a recording | ask |
| `profile_write` | Saving device and workspace facts | allow |
| `setup_plan` | Editing the setup plan | allow |
| `calib_compute` | Running calibration solvers | ask |
| `shell`, `write`, `edit` | Pi's shell and file-editing tools | ask |

To change the defaults, set rules in `.kinex/kinex.json` for one project or `~/.config/kinex/kinex.json` for all of them. Each value is `allow`, `ask` or `deny`; the project file wins.

```json
{
  "permission": {
    "device_read": "allow",
    "device_act": "ask",
    "shell": "ask"
  }
}
```

A few rules always hold, whatever the mode:

- Stopping never needs approval. `/stop` cancels the agent's response and stops actuators in every mode.
- One approval for `exec` covers every device call that script makes.
- Only your commands and the `device` tool can load or unload devices. Python tools and scripts cannot.
- Calls run one at a time, so denying one stops the rest of the batch. Calls that already ran are not rolled back.

Approvals are a safeguard, not a sandbox. They don't isolate the agent from your system, and they don't make motion safe on their own: some operations can't be interrupted by their driver, so know where your hardware emergency stop is.

## Spatial relationships

The runtime keeps a graph of every frame it knows: each device's base, the frames computed from an arm's joint model, and the mounts declared in each profile's extrinsics. Arm frames are recomputed from measured joint positions, so the graph follows the robot as it moves.

`relative_pose` asks this graph a question: where is one frame, or a pose attached to it, relative to another? For example, the pose of an object seen by the wrist camera, expressed in the arm's base frame:

```json
{
  "child":  {"frame": "wrist_cam", "pose": [0.02, -0.01, 0.35, 0, 0, 0, 1]},
  "parent": {"frame": "arm"}
}
```

The runtime finds the path between the two frames, chains the transforms along it, and returns the pose together with the path it used. If any link on that path is unknown, the call fails rather than guessing. You can pass an estimate for a missing link in the call itself; it applies only to that call and is never saved.

An arm's frames and its forward and inverse kinematics both come from its joint model; `servo` calls the arm's inverse kinematics to turn a pose target into a joint trajectory. See [Devices](/docs/devices/#space-frames-and-extrinsics).

## Time and motion

The runtime owns the link between motion and the [world clock](/docs/devices/#time-the-world-clock). `servo` waits out its planned trajectory and `closed_loop` waits `wait_s` after each control step, both on the `world` clock, so a stepped simulator advances only by those waits. When a call is cancelled, the runtime stops only the motion that call started, leaving commands from other calls in place.

## Python environment

Drivers, Python tools and `exec` scripts all run in one Python environment per workspace, `.kinex/python/`, managed with [uv](https://docs.astral.sh/uv/). Kinex creates it the first time it is needed and never touches your own Python projects. Inside it, the `kinex` library gives scripts the same device access the agent has:

```python
from kinex import device, devices

frame = device("camera", "read", {"output": "file"})
```

See [Custom tools & skills](/docs/custom-tools/).

## Context for the agent

Before each request, the runtime gives the agent an up-to-date picture of the workspace: which devices exist and which are loaded, how they're mounted, what still needs calibration, the usage guide for each loaded device type, shared conventions such as frames and units, the available skills and the Python environment. Changes are appended to the conversation, not rewritten, and this context is restored after the conversation is compacted. See [Working with the agent](/docs/agent/#context-and-compaction).
