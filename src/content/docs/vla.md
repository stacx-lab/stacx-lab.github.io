---
title: Using VLAs as tools
description: Register a vision-language-action model as a device, run it with run_policy, and control bounded observation/action cycles with Python exec.
group: Guides
order: 40
label: Using VLAs as tools
sources: ["packages/core/README.md", "docs/tools-and-skills.md", "packages/core/assets/builtin/tool/run-policy/tool.yaml", "packages/core/assets/builtin/device/templates/model/DEVICE.md", "packages/core/assets/builtin/skill/setup-device/SKILL.md"]
---

A vision-language-action model (VLA) takes camera images and a task description and predicts the robot's next moves. In Kinex, a VLA is not the agent; it's a tool the agent uses. The agent decides when to run the policy, on which devices, for how long, and when to stop.

This takes three pieces:

1. **The VLA becomes a device.** It's registered like a camera or an arm, as a `model` device with an `infer` operation.
2. **`run_policy` runs it once.** It sends one observation to the model and passes the predicted actions to the robot.
3. **Python `exec` coordinates the cycle.** It gathers fresh observations, runs bounded policy chunks, checks feedback and returns images for the agent to assess.

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

## 3. Observe, act and inspect with `exec`

Use Python variables and a bounded loop to gather observations and run policy chunks. This example runs at most three chunks, then stops owned motion and returns all three camera views for the agent's next decision:

```python
from kinex import call, device, finish, stop_owned

cameras = {"head_image": "head_camera", "left_image": "left_camera",
           "right_image": "right_camera"}
actuators = ["left_arm", "left_gripper", "right_arm", "right_gripper"]
commands = [{"device": name} for name in actuators]
chunks = []
try:
    for _ in range(3):
        for name in actuators:
            state = device(name)
            if state["faults"]:
                raise RuntimeError(f"{name}: {state['faults']}")
        observation = {
            key: device(camera, args={"output": "file"})["file"]
            for key, camera in cameras.items()
        }
        chunk = call("run_policy", model="starvla", observation=observation,
                     task="place the bottle in the basket", command=commands,
                     action_hz=25, max_actions=25)
        if chunk["ik_failure"] or chunk["actions_submitted"] == 0:
            raise RuntimeError(f"policy chunk rejected: {chunk}")
        chunks.append(chunk)
        device("world", "wait", {"duration_s": chunk["duration_s"]})
finally:
    stop_owned()

feedback = {name: device(name) for name in actuators}
for name, state in feedback.items():
    if state["faults"]:
        raise RuntimeError(f"{name}: {state['faults']}")
observations, images = [], []
for camera in cameras.values():
    frame = device(camera, args={"output": "file"})
    observations.append({"deviceID": camera, "timestamp": frame["timestamp"]})
    images.append(frame["file"])
finish({"reason": "inspection required", "chunks": chunks,
        "feedback": feedback, "observations": observations}, file=images)
```

Adapt the camera names, action order and feedback checks to the actual model and robot. The three-chunk limit bounds this example; it does not establish task success. If each chunk needs visual interpretation, run just one and return images before continuing. Ask the agent to run a short policy segment, inspect whether the bottle reached the basket, and decide what comes next.

- **Timing.** `run_policy` returns immediately with `actions_submitted`, `duration_s`, `execution_ids` and `ik_failure`. Wait on the `world` clock for the returned duration before assessing the resulting state. In a stepped simulator, inference time does not advance the world.
- **Rejected actions.** IK rejection can return normally with a shortened or empty valid prefix. Inspect `ik_failure`; a successful tool call does not imply the whole chunk was accepted.
- **Replanning.** A new chunk can replace the remaining references of the previous one. Choose an explicit shorter world-wait interval if the task needs replanning during execution.
- **Cleanup.** `stop_owned()` in `finally` requests a stop on every exit. Runtime failure, timeout or cancellation also triggers cleanup attempts; successful execution alone does not stop motion.

The former `closed_loop` and `settled` tools are no longer bundled. See [Feedback control](/docs/custom-tools/#feedback-control) for a measured joint-target check, and [vision models](/docs/vision/) for perception-driven motion.
