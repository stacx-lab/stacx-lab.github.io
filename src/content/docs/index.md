---
title: Kinex documentation
description: A general harness for arbitrary robots with coding agents — skills, tools and devices on top of the Pi coding agent.
group: Get started
order: 10
label: Overview
sources: ["README.md", "install.sh", "docs/architecture.md", "docs/overview.md", "packages/core/README.md", "packages/setup/README.md", "src/application.ts"]
---

Kinex is a general harness for arbitrary robots with coding agents, built on the [Pi](https://pi.dev) coding agent. It gives an agent three layers to work with:

| Layer | Gives the agent | Example |
| --- | --- | --- |
| **Skills** | Task procedures the agent loads on demand | `setup-device`, `calibrate-camera-extrinsics` |
| **Tools** | Executable operations over devices and computation | `device`, `exec`, `servo`, `locate_object_3d` |
| **Devices** | Typed access to hardware, simulators and model services | `arm`, `wrist_cam`, `world`, `sam3` |

Kinex lets you work with real hardware the way you already work with a coding agent. Describe the task in plain language and the robot carries it out.

## Install and run

```sh
curl -fsSL https://raw.githubusercontent.com/stacx-lab/kinex/main/install.sh | bash
cd /path/to/robot-workspace
kinex
```

Then `/login` to connect a model provider and `/model` to choose a model.

| Need | For |
| --- | --- |
| macOS or Ubuntu | Installing and running Kinex |
| Node.js ≥ 22.19 + npm | Kinex itself (the installer can install them) |
| `curl` | The installer |
| Python ≥ 3.11 + [uv](https://docs.astral.sh/uv/) | Python tools, drivers, `exec` |
| `ffmpeg` | Video encoding during [recording](/docs/recording/) |

**Already use Pi, Claude Code or Codex?** Kinex plugins currently support these three harnesses: see [Plugin systems](/docs/plugins/).

## Pick a path

<nav class="doc-paths" aria-label="Choose your getting started guide">
  <a class="doc-path" href="/docs/simulators/">
    <span class="doc-path-copy">
      <strong>Playing with a simulator?</strong>
      <span>Launch a task in RoboEnv, such as loading condiments into a fridge in RoboCasa, and drive its robot with Kinex.</span>
    </span>
    <span class="doc-path-arrow" aria-hidden="true">→</span>
    <span class="doc-path-destination">Simulators</span>
  </a>
  <a class="doc-path" href="/docs/real-robots/">
    <span class="doc-path-copy">
      <strong>Working with real robots?</strong>
      <span>Describe your hardware and task with <code>/onboarding</code> to connect and calibrate your robot.</span>
    </span>
    <span class="doc-path-arrow" aria-hidden="true">→</span>
    <span class="doc-path-destination">Real robots</span>
  </a>
  <a class="doc-path" href="/docs/ros2/">
    <span class="doc-path-copy">
      <strong>Already using ROS 2?</strong>
      <span>Connect your existing ROS 2 hardware with <code>/onboarding</code> or <code>/register</code>.</span>
    </span>
    <span class="doc-path-arrow" aria-hidden="true">→</span>
    <span class="doc-path-destination">ROS 2 onboarding</span>
  </a>
</nav>

## Understand the design of Kinex

- [Architecture](/docs/architecture/) — skills, tools, devices and who owns what.
- [Devices](/docs/devices/) — types, profiles, drivers, frames and clocks.
- [Tools & skills](/docs/tools-and-skills/) — the built-in tools and skills, and how custom ones are discovered.
- [Runtime](/docs/runtime/) — what Kinex handles for you: devices, discovery, permissions, frames, time and context.

## Go further

| Task | Page |
| --- | --- |
| Choose a model and approval mode; manage conversations, compaction and sessions | [Working with the agent](/docs/agent/) |
| Set up new hardware and calibrate it | [Onboarding & calibration](/docs/onboarding/) |
| Run Python, add your own tools and skills | [Custom tools & skills](/docs/custom-tools/) |
| Run VLA policies and feedback loops | [Using VLAs as tools](/docs/vla/) |
| Find and locate objects with vision models | [Using vision models as tools](/docs/vision/) |
| Record what the robot sees and does | [Recording](/docs/recording/) |
| Install Pi plugins, or use Kinex from other harnesses | [Plugin systems](/docs/plugins/) |

Reference: [CLI](/docs/cli/), [slash commands](/docs/slash-commands/), [troubleshooting](/docs/troubleshooting/).

## About this version

These pages describe **Kinex 1.0.0**, bundling the **Pi coding agent 1.2.0** (`@earendil-works/pi-coding-agent`). No separate Pi install is needed. Install on macOS and Ubuntu. Node.js ≥ 22.19 is required.

The documentation tracks source commit `afeddc6` (2026-10-14). Source references are recorded in each page's metadata. Kinex and its core/setup packages use the [Apache License, Version 2.0](https://github.com/stacx-lab/kinex/blob/afeddc698d14ea9fb5ae0e88f51fecd89000dec4/LICENSE). Bundled third-party notices are listed in [THIRD_PARTY_NOTICES.txt](https://github.com/stacx-lab/kinex/blob/afeddc698d14ea9fb5ae0e88f51fecd89000dec4/THIRD_PARTY_NOTICES.txt).
