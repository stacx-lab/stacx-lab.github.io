---
title: Kinex v1.0.0
date: 2026-10-15
summary: Devices, tools and skills. A curl installer, ROS 2 provisioning, runtime Python and Pi packages.
tags: [release]
---

Kinex 1.0 is out. It is a robotics harness for coding agents, built on the Pi coding agent.

```sh
curl -fsSL https://raw.githubusercontent.com/stacx-lab/kinex/main/install.sh | bash
```

## What's in 1.0

- **Three layers.** Devices give typed access to hardware, simulators and model services. Tools run operations on them. Skills tell the agent how to do a task. See [architecture](/docs/architecture/).
- **One-line install and updates.** `install.sh` reuses Node ≥ 22.19 or offers to install it. `kinex update` updates Kinex and its bundled Pi coding agent.
- **ROS 2 provisioning.** Onboarding can provision isolated ROS 2 Jazzy device bundles and adapters, with lazy transport and feedback helpers.
- **Runtime Python.** The `exec` tool runs plain Python source or scripts with runtime access. A `tool.yaml` manifest is only needed for reusable tools.
- **Pi packages.** Use `kinex install`, `kinex list`, `kinex remove` and `kinex update --extensions` to manage extensions, skills, prompts and themes.
- **Better feedback.** Camera images appear inline in device tool results. Measured interface checks during setup are unified, and the footer shows active session time.
- **Other harnesses.** Plugins for Pi, OpenCode and Codex ship Kinex's core in [kinex-plugins](https://github.com/stacx-lab/kinex-plugins).

## Upgrading from 0.10

```sh
kinex update
```

Device APIs and discovery directories were aligned for 1.0. Run `/devices` and `/ping all` after upgrading. If something does not connect, reload it with `/unload <device>` and then `/load <device>`. The [command reference](/docs/slash-commands/) lists the current commands.
