---
title: Tools & skills
description: The built-in tool catalog, the bundled skills, and how discovery works.
group: Concepts
order: 30
sources: ["docs/tools-and-skills.md", "packages/core/README.md", "packages/setup/README.md", "src/integration/tools.ts"]
---

Tools execute; skills instruct. Both complement the host's coding tools (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`).

## Tools

| Tool | Does |
| --- | --- |
| `device` | Call one device: read, write, run inference, or `load`/`unload` it |
| `devices` | Call several devices at once; each call reports its own result or error |
| `device_stop` | Stop one device or all loaded actuators; never needs approval |
| `exec` | Run Python source or a script file with device access, feedback control and selected image results |
| `record` | Start and stop recordings; available only with `--enable-recording` |
| `skill` | Load a skill's instructions into the conversation |
| `profile_write` | Validate and save workspace and device facts, including calibration requests |
| `relative_pose` | Express a frame or pose relative to another frame |
| `locate_object_3d` | Combine a camera, a detection model and depth to find an object's 3D position |
| `servo` | Plan and send a joint trajectory to joint or pose targets; waits on the world clock by default (`block: false` returns immediately) |
| `run_policy` | Run a policy model once and send its actions to the devices |
| `setup_plan` | Read and update the task's setup plan and record each step's outcome (`@kinex/setup`) |
| `calib_sample` | Capture one measured sample for a calibration (`@kinex/setup`) |
| `calib_compute` | Run a calibration solver and propose the resulting profile changes (`@kinex/setup`) |
| `question` | Ask you a structured question (standalone Kinex only) |
| `kinex_skill` | Load a skill from any Kinex package (standalone Kinex only) |

Use bounded Python scripts in `exec` to combine control, fresh feedback and camera observations. The former `closed_loop` and `settled` built-ins have been removed; put their loop state and task-specific stopping checks in Python. See [Feedback control](/docs/custom-tools/#feedback-control).

More detail: [Using vision models as tools](/docs/vision/), [Using VLAs as tools](/docs/vla/).

## Bundled skills

| Skill | Package | Purpose |
| --- | --- | --- |
| `setup-device` | core | Pick a guide, provision a driver, write a profile, verify; also repair |
| `onboard-ros2` | setup | ROS 2 Jazzy integrations — see [ROS 2 onboarding](/docs/ros2/) |
| `calibrate-*`, `verify-base-*` | setup | Measurement procedures — see [Calibration](/docs/onboarding/#calibration) |

## Discovery

Kinex looks for tools and skills in a `.kinex/` folder, searching these places in order:

1. the `.kinex/` nearest the current directory;
2. `.kinex/` folders in enclosing directories further up;
3. your global config, `~/.config/kinex/`;
4. the tools and skills built into Kinex.

When two places define the same name, the first one found wins. A project can therefore override a global or built-in Python tool or skill by defining one with the same name.

Custom discovery uses the plural `tools/` and `skills/` directories, including in global config. Move older custom content out of singular `tool/` and `skill/` directories. Packaged `assets/builtin/tool/` and `assets/builtin/skill/` paths are unchanged.

### Tools

```text
.kinex/tools/
├── my_tool/
│   ├── tool.yaml     # name, kind, description, parameters (JSON Schema)
│   └── tool.py       # implementation
└── helpers.ts        # JS/TS tools, one or more per file
```

- **Python tools** live in their own folder with a `tool.yaml` manifest and a `tool.py`. The tool's name comes from `name` in the manifest.
- **JS/TS tools** are `.ts` or `.js` files placed directly in `tools/`. Each export with a `description` and an `execute` function (plus an optional Zod `parameters` schema) becomes a tool. A default export is named after the file; any other export is named `<file>_<export>`.
- Tools are rescanned on every agent step, so a tool you write or edit mid-task is available at the next step.
- The core tools listed above (`device`, `exec`, `skill` and so on) always take priority. A custom tool with the same name is skipped, and Kinex reports the conflict.

### Skills

```text
.kinex/skills/
└── pick-and-place/
    ├── SKILL.md      # frontmatter (name, description), then instructions
    └── references/   # optional supporting files
```

- Kinex finds every `SKILL.md` under `skills/`, at any depth. The skill's name comes from `name` in the frontmatter, or the folder name if that is missing.
- The agent sees each skill's name and description up front. When a description matches the task, it loads the full instructions with the `skill` tool.
- Write the `description` carefully. It is what the agent uses to decide whether to load the skill.

Write your own: [Custom tools & skills](/docs/custom-tools/).
