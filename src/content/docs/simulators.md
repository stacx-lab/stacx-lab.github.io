---
title: Playing with simulators
label: Simulators
description: Launch a simulator task through RoboEnv and drive its robot as Kinex devices.
group: Get started
order: 20
sources: ["README.md", "docs/devices.md", "docs/commands.md", "packages/core/assets/builtin/device/templates/world/DEVICE.md", "packages/core/src/commands.ts"]
---

[RoboEnv](https://github.com/stacx-lab/RoboEnv) runs simulator tasks (RoboCasa, LIBERO, RoboTwin, RoboDojo, BEHAVIOR, Isaac Lab, SIMPLE, ABC) and exposes their robots as Kinex devices. Kinex itself ships no simulator engine — just the device contracts RoboEnv implements.

Assumes Kinex is installed (see [Install and run](/docs/#install-and-run)).

## 1. Launch a simulator

RoboEnv runs from a source checkout on Linux with Git and [uv](https://docs.astral.sh/uv/). Clone and bootstrap it once:

```sh
git clone https://github.com/stacx-lab/RoboEnv.git
cd RoboEnv
bash tools/bootstrap.sh
source .venv/bin/activate
```

Bootstrap installs the `roboenv` CLI into a Python 3.12 environment. Activate it in each new shell, or call `.venv/bin/roboenv` directly.

Choose a task and its paired robot/device configuration:

```sh
roboenv tasks list --simulator robocasa
roboenv robots list --simulator robocasa
```

Both commands print one ID per line. Omit `--simulator` to see all entries, or add `--json` for structured output. `launch` takes a **task ID**; `setup` takes its **robot ID**, which exports the robot's full device collection. Read `robot:` in RoboEnv's `catalog/tasks/<task-id>/task.yaml` for the exact pairing. A simulator may have several robots or scene configurations, so sharing a simulator name is not enough.

| Task ID for `roboenv launch` | Robot ID for `roboenv setup` |
| --- | --- |
| `robocasa/load-condiments-in-fridge` | `robocasa/robocasa-panda-omron` |
| `robotwin/handover-block-aloha-agilex` | `robotwin/robotwin-aloha-agilex` |
| `abc/hang-mug-on-mug-rack` | `abc/abc-yam` |

Prepare the simulator, then launch the task. This page uses the RoboCasa pair:

```sh
roboenv prepare robocasa
roboenv launch robocasa/load-condiments-in-fridge --port 8123
```

`prepare` installs the simulator's isolated interpreter and downloads its assets (RoboCasa needs about 10 GB). It is only needed once per simulator. Wait for `Ready` and leave `launch` running; Ctrl+C stops the environment.

For another simulator, run `roboenv prepare <name>` and pick a task from `roboenv tasks list --simulator <name>`. GPU prerequisites and per-simulator assets are in RoboEnv's [setup guide](https://github.com/stacx-lab/RoboEnv/blob/main/docs/setup.md).

## 2. Create a Kinex workspace

In a second terminal, activate the same environment and create a workspace:

```sh
source /path/to/RoboEnv/.venv/bin/activate         # put the roboenv CLI on PATH
mkdir -p kinex-sim-workspace                       # the Kinex workspace directory
cd kinex-sim-workspace
roboenv setup robocasa/robocasa-panda-omron         # export the robot into .kinex/
export ROBOENV_ENDPOINT=http://127.0.0.1:8123       # where the drivers find the running scene
roboenv describe --endpoint "$ROBOENV_ENDPOINT"   # read the initialized task instruction
kinex
```

`roboenv setup <simulator/robot>` copies a ready-made robot configuration from RoboEnv's catalog into the current directory's `.kinex/`, creating it if needed:

- `workspace.yaml`: the robot manifest.
- `devices/`: one profile and thin driver per device. For the RoboCasa Panda–Omron that is `arm`, `base`, `torso`, `gripper`, three cameras and `world`.

`setup` exports devices without installing or launching a simulator. The configuration is task-independent, so one workspace serves every task with the same robot ID. `roboenv robots list --simulator robocasa` lists robot IDs for RoboCasa; `roboenv setup --list` remains available for listing all robots. For a different robot ID, create a new workspace or save custom configuration before `roboenv setup ROBOT_ID --force`, which replaces the manifest and entire device collection.

`ROBOENV_ENDPOINT` tells the drivers which running scene to connect to; match the `launch` port.

## 3. Inspect devices

Inside the Kinex session:

```text
/devices
/load all
/ping all
```

`/devices` shows saved activation intent (`loaded`), not liveness. `/ping` checks live status without starting anything.

## 4. Give it a task

Give Kinex the running task's `task.instruction` and `task.context` from `roboenv describe`. For the example above, ask it to inspect the scene and complete that fridge task using the paired robot's devices. To inspect the scene first:

```text
Look through the robot's cameras and describe what is in the scene.
```

Approve the device read when asked (or switch with `/mode`; see [Approval modes](/docs/agent/#approval-modes)). Camera images come back attached to the tool result. Press **Ctrl+O** to expand tool calls and check the raw observation against the agent's answer.

## 5. Record the episode

Add `--record` when you launch to film the episode from RoboEnv's spectator cameras:

```sh
roboenv launch robocasa/load-condiments-in-fridge --port 8123 --record                         # under the run's evidence/recording/
roboenv launch robocasa/load-condiments-in-fridge --port 8123 --record ./recordings/episode-1  # into this directory
```

You get one MP4 per view; it needs `ffmpeg` on `PATH`. More options: RoboEnv's [spectator recording guide](https://github.com/stacx-lab/RoboEnv/blob/main/docs/spectator.md).

## 6. Finish and Reconnect

Leave Kinex with `/quit`. Then stop the simulator: press **Ctrl+C** in the `launch` terminal, or, if you launched with `--detach`, run `roboenv stop <run-id>` from the RoboEnv checkout with the run ID that `launch` printed (add `--project /path/to/RoboEnv` when running it elsewhere).

After restarting the simulator or changing profiles, reconnect the devices in Kinex:

```text
/unload all
/load all
```

After upgrading Kinex, refresh the copied RoboEnv profiles and drivers together (`roboenv setup <simulator/robot> --force`) and restart the simulator.

More tasks and connection details: RoboEnv's [Kinex walkthrough](https://github.com/stacx-lab/RoboEnv/blob/main/docs/kinex-local.md).
