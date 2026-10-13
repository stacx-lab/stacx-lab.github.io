---
title: Kinex documentation
description: A robotics harness for coding agents — skills, tools and devices on top of the Pi coding agent.
group: Get started
order: 10
label: Overview
sources: ["README.md", "install.sh", "docs/architecture.md", "docs/overview.md", "packages/core/README.md", "packages/setup/README.md", "src/application.ts"]
---

Kinex is a robotics harness for coding agents, built on the [Pi](https://pi.dev) coding agent. It gives an agent three layers to work with:

| Layer | Gives the agent | Example |
| --- | --- | --- |
| **Skills** | Task procedures the agent loads on demand | `setup-device`, `calibrate-camera-extrinsics` |
| **Tools** | Executable operations over devices and computation | `device`, `exec`, `servo`, `locate_object_3d` |
| **Devices** | Typed access to hardware, simulators and model services | `arm`, `wrist_cam`, `world`, `sam3` |

Kinex lets you work with real hardware the way you already work with a coding agent. Describe the task in plain language and the robot carries it out.

## Core and setup

Kinex has two reusable robotics packages:

| Package | What it provides |
| --- | --- |
| **`@kinex/core`** | The robotics runtime: devices and drivers, tools and skills for registering and operating devices, motion control, perception and recording. |
| **`@kinex/setup`** | Task-scoped onboarding and calibration, including ROS 2 setup, built on top of core. |

Core can operate devices independently of setup. The standalone **`kinex`** app combines both packages with the Pi coding agent, which supplies the conversation loop and terminal interface. See [Architecture](/docs/architecture/#packages) for more detail.

## Install and run

```sh
curl -fsSL https://raw.githubusercontent.com/stacx-lab/kinex/main/install.sh | bash
cd /path/to/robot-workspace
kinex
```

Then `/login` to connect a model provider and `/model` to choose a model.

| Need | For |
| --- | --- |
| Linux or macOS | The installer refuses other platforms |
| Node.js ≥ 22.19 + npm | Kinex itself (the installer can install them) |
| `curl` | The installer |
| Python 3 + [uv](https://docs.astral.sh/uv/) | Python tools, drivers, `exec` |
| `ffmpeg` | Video encoding during [recording](/docs/recording/) |

**Already use Pi, OpenCode or Codex?** You can use Kinex capabilities from those harnesses instead: see [Plugin systems](/docs/plugins/).

## Pick a path

- **Playing with a simulator?**\
  Launch a task in [RoboEnv](https://github.com/stacx-lab/RoboEnv) (RoboCasa, LIBERO, RoboTwin, Isaac Lab and more) and drive its robot like a real one. See [Simulators](/docs/simulators/).
- **Working with real robots?**\
  Describe your hardware and task with `/onboarding`. See [Real robots](/docs/real-robots/), then [Onboarding & calibration](/docs/onboarding/) for the details, including ROS 2.

## Understand the design of Kinex

- [Architecture](/docs/architecture/) — skills, tools, devices and who owns what.
- [Devices](/docs/devices/) — types, profiles, drivers, frames and clocks.
- [Tools & skills](/docs/tools-and-skills/) — the built-in tools and skills, and how custom ones are discovered.
- [Runtime](/docs/runtime/) — what Kinex handles for you: devices, discovery, permissions, frames, time and context.

## Go further

| Task | Page |
| --- | --- |
| Choose a model and approval mode; manage conversations, compaction and sessions | [Working with the agent](/docs/agent/) |
| Set up new hardware, including ROS 2, and calibrate it | [Onboarding & calibration](/docs/onboarding/) |
| Run Python, add your own tools and skills | [Custom tools & skills](/docs/custom-tools/) |
| Run VLA policies and feedback loops | [Using VLAs as tools](/docs/vla/) |
| Find and locate objects with vision models | [Using vision models as tools](/docs/vision/) |
| Record what the robot sees and does | [Recording](/docs/recording/) |
| Install Pi plugins, or use Kinex from other harnesses | [Plugin systems](/docs/plugins/) |

Reference: [CLI](/docs/cli/), [slash commands](/docs/slash-commands/), [troubleshooting](/docs/troubleshooting/).

## About this version

These pages describe **Kinex 1.0.0**, bundling the **Pi coding agent 1.1.0** (`@earendil-works/pi-coding-agent`). No separate Pi install is needed. Linux and macOS are supported; Node.js ≥ 22.19 is required.
