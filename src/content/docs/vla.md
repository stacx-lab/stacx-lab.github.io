---
title: Using VLAs as tools
description: Register a vision-language-action model as a device, run it with run_policy, and close the loop with closed_loop.
group: Guides
order: 40
label: Using VLAs as tools
sources: ["packages/core/README.md", "docs/tools-and-skills.md", "packages/core/assets/builtin/tool/run-policy/tool.yaml", "packages/core/assets/builtin/tool/closed-loop/tool.yaml", "packages/core/assets/builtin/device/templates/model/DEVICE.md", "packages/core/assets/builtin/skill/setup-device/SKILL.md"]
---

A vision-language-action model (VLA) takes camera images and a task description and predicts the robot's next moves. In Kinex, a VLA is not the agent; it's a tool the agent uses. The agent decides when to run the policy, on which devices, for how long, and when to stop.

This takes three pieces:

1. **The VLA becomes a device.** It's registered like a camera or an arm, as a `model` device with an `infer` operation.
2. **`run_policy` runs it once.** It sends one observation to the model and passes the predicted actions to the robot.
3. **`closed_loop` repeats it.** It keeps observing, running the policy and waiting until the task is done.

This page uses [StarVLA](https://github.com/starVLA/starVLA) on a RoboTwin dual-arm robot as the example.

## 1. Register the VLA as a device

Let the agent set it up. Tell `/register` which model you want and what robot it's for:

```text
/register model StarVLA/Qwen3-VL-OFT-RoboTwin2-All policy for the dual-arm RoboTwin robot
```

The agent follows the built-in `setup-device` skill. It reads the model's documentation, downloads and pins the weights, builds an isolated Python environment for the model, writes a driver and a profile, and checks what it can without loading the model. The device is left unloaded. Loading it puts the model on the GPU, so load it only when you need it:

```text
/load starvla
```

The result is an ordinary device in `.kinex/devices/starvla/`. Its profile records where the model runs and, most importantly, what it takes in and gives back:

```yaml
name: starvla
type: model
access:
  connection: {kind: process, compute: {kind: cuda, index: 3}}
intrinsics:
  family: starVLA
  variant: Qwen3-VL-OFT-RoboTwin2-All
  operations:
    - name: infer
      input:   # three camera images (file paths) and a task instruction
        obs: {head_image, left_image, right_image}
        task: string
      output:  # 50 steps × 14 values
        actions: [[left_arm ×6, left_gripper, right_arm ×6, right_gripper], ...]
```

*(Abridged; the real profile spells this out as JSON Schema.)*

Each prediction is a chunk of 50 actions. Each action holds 14 numbers: six joint positions and a gripper value for each arm. The model only predicts. It never moves the robot itself.

## 2. Run the policy once with `run_policy`

`run_policy` connects the model to the robot. It sends the observation and task to the model, splits each predicted action across the devices you list, and sends the result to them:

```json
{
  "model": "starvla",
  "observation": {
    "head_image": "/tmp/obs/head.png",
    "left_image": "/tmp/obs/left.png",
    "right_image": "/tmp/obs/right.png"
  },
  "task": "place the bottle in the basket",
  "command": [
    {"device": "left_arm"},
    {"device": "left_gripper"},
    {"device": "right_arm"},
    {"device": "right_gripper"}
  ],
  "action_hz": 25,
  "max_actions": 25
}
```

- **`command`** lists the devices in the same order as the model's output. Here that's 6 values for `left_arm`, 1 for `left_gripper`, and so on. Values are sent as absolute joint positions by default. A model that predicts end-effector poses or pose changes can set `"space": "pose"` or `"pose_delta"`, and Kinex converts them to joint positions with inverse kinematics.
- **`action_hz`** is how fast the actions are played back.
- **`max_actions`** limits how much of the chunk is used. Here only the first 25 of the 50 actions, one second of motion, are sent. The robot then gets a fresh prediction instead of following a stale plan.

`run_policy` returns as soon as the actions are sent, reporting how many went out and for how long. It doesn't wait for the motion to finish; that's the loop's job.

## 3. Close the loop with `closed_loop`

One policy call moves the robot for a moment. To finish a task, you observe, predict, act and repeat. `closed_loop` runs that cycle for you:

```text
perceive → process → control → wait → until
   ↑                                    │
   └──────────── not done ──────────────┘
```

| Stage | Role | For a VLA |
| --- | --- | --- |
| `perceive` | Gather fresh observations | Save the three camera images |
| `process` | Turn observations into the next command's arguments | Pass the images on as the policy's `observation` |
| `control` | Act | `run_policy` on the next chunk |
| *wait* | Let the world advance by `wait_s` | Let the submitted actions play out |
| `until` | Decide whether to stop | Check whether the task is done |

`until` is also checked once before the first round.

Each stage is either a tool or a short piece of Python. Here is the loop for the example, as the agent would run it from an `exec` script:

```python
from kinex import call

call("closed_loop", world="world", wait_s=1.0, max_rounds=30,
    perceive={"python": """
from kinex import device
def main():
    cams = {"head_image": "head_camera", "left_image": "left_camera", "right_image": "right_camera"}
    return {k: device(cam, args={"output": "file"})["file"] for k, cam in cams.items()}
"""},
    process={"python": "lambda observation: {'observation': observation}"},
    control={"tool": "run_policy", "args": {
        "model": "starvla", "task": "place the bottle in the basket",
        "command": [{"device": "left_arm"}, {"device": "left_gripper"},
                    {"device": "right_arm"}, {"device": "right_gripper"}],
        "action_hz": 25, "max_actions": 25}})
```

Each round reads the cameras, runs the policy on the next 25 actions, and waits one second of world time while they play out. Then it starts again with fresh images. With no `until` stage, the loop runs until `max_rounds`. Add one, as a tool or Python that checks the scene, to stop as soon as the task is done.

You rarely write this by hand. Ask the agent to "run the StarVLA policy to place the bottle in the basket, re-planning every second", and it builds the loop, watches the result and adjusts.

A few things the loop handles for you:

- **Timing.** Waits use the `world` clock, so in a stepped simulator each round advances simulated time by exactly `wait_s`, however long inference takes in real time.
- **Replanning.** A new chunk replaces whatever is left of the previous one, so `wait_s` sets how often the robot replans. Short waits react faster but can stall motion; long waits react slowly.
- **Stopping safely.** On an error, a cancel, too many missed observations (`max_misses`) or the end of the loop, `closed_loop` stops the motion it started.
- **Honest results.** The loop reports why it ended. Running out of rounds is not the same as success.

The same loop works for more than VLAs. For example, it can track a moving target with `relative_pose` and `servo`, using `settled` as the stopping check. See [Tools & skills](/docs/tools-and-skills/).
