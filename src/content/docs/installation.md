---
title: Installation
description: Install Kinex, open a robot workspace, and connect a model provider.
group: Get started
order: 15
sources: ["README.md", "install.sh"]
---

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
