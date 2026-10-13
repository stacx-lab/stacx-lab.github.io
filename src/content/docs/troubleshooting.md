---
title: Troubleshooting
description: Fixes for common problems with installation, models, approvals, devices and Python.
group: Reference
order: 30
sources: ["install.sh", "src/cli.ts", "src/arguments.ts", "src/auth.ts", "docs/overview.md", "docs/devices.md", "packages/core/README.md"]
---

First, check which version you're running and which workspace and devices Kinex sees:

```sh
kinex --version
kinex run "/devices"
```

## Installation and startup

| Problem | Fix |
| --- | --- |
| `kinex: command not found` | Add `~/.local/bin` to your `PATH`; the installer prints the exact line |
| `Another Kinex is on PATH` | Another `kinex` is installed and first on your `PATH`. Either keep it and run `kinex update`, or remove it and rerun the installer. |
| `Refusing to replace ~/.local/bin/kinex` | A file the installer didn't create is in the way. Move it, then reinstall. |
| Syntax errors, or Node.js too old | Kinex needs Node.js 22.19 or newer. Rerun the installer to get one. |
| `Unsupported option` or `--json was removed` | The option changed in 1.0.0; see [Changed in 1.0.0](/docs/cli/#changed-in-100) |
| `--resume requires a terminal` | In scripts, use `--continue` or `--session <id>` instead |
| `AuthPathConflict` | `~/.config/kinex/agent/auth.json` holds credentials that Kinex expects in `~/.local/share/kinex/agent/auth.json`. Move or merge them into the latter, delete the former, then restart. |

## Models and approvals

| Problem | Fix |
| --- | --- |
| Model not found | Check the exact name in `/model`. `--provider` only works together with `--model`. |
| Authentication errors | Run `/login` again, or check the provider's API-key environment variable |
| Local model doesn't respond | Make sure the model server is running before you start Kinex |
| Tool calls denied in a scripted run | Without a terminal, `ask` can't prompt you, so calls are denied. Allow specific permissions in `.kinex/kinex.json`, or use `--auto`. See [Permissions](/docs/runtime/#permissions). |

## Devices

| Problem | Fix |
| --- | --- |
| `device "x" is unloaded` | Run `/load x`. |
| Shows as loaded but doesn't respond | Being marked as loaded doesn't mean it's connected. Run `/ping x`, then `/unload x` and `/load x`. |
| Loading fails | Fix the driver or connection, then `/load` again. Kinex never restarts a failed device on its own. |
| `No robot is configured` | No valid `.kinex/workspace.yaml` was found: it's missing or invalid. Check you're in the right directory. |
| The wrong devices show up | A `.kinex/` folder closer to your current directory is hiding the one you meant |
| Old behavior after an update | Drivers and tools copied into the workspace override the updated ones. Refresh those copies. |
| `stop_failed` | The device couldn't be stopped cleanly. New commands are blocked until it's recovered; check the hardware, then unload and load it. |

## Python

| Problem | Fix |
| --- | --- |
| `uv` not found | Install [uv](https://docs.astral.sh/uv/). It's only needed to create the workspace's Python environment. |
| A package is missing | Run `uv add --project .kinex/python <package>`. Kinex doesn't install new dependencies on its own. |
| ROS driver fails to import | ROS drivers use the system Python 3.12, not `.kinex/python` |

## Reporting an issue

Open an issue at [stacx-lab/kinex/issues](https://github.com/stacx-lab/kinex/issues) and include:

- the output of `kinex --version`, your OS, and your Node.js and Python versions;
- the command you ran, what you expected, and what happened, including the error;
- whether the device is simulated or real.

Remove credentials and any private images first.
