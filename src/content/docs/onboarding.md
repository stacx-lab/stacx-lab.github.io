---
title: Onboarding & calibration
description: How Kinex brings up new hardware and calibrates what a task needs.
group: Guides
order: 20
label: Onboarding & calibration
sources: ["packages/setup/README.md", "packages/setup/src/workflows/onboarding.txt", "packages/setup/src/workflows/calibrate.txt", "packages/core/assets/builtin/skill/setup-device/SKILL.md", "docs/setup.md"]
---

Getting a new robot ready means two things: describing the hardware so Kinex can talk to it (**onboarding**), and measuring the physical facts a task depends on (**calibration**). Both are guided by the agent, and both are driven by your task: Kinex prepares and measures only what that task needs.

<div class="caveat">
<p class="caveat-title">Before you start</p>
<ul>
<li><b>Not fully hands-off.</b> Onboarding and calibration still need you to:
<ul>
<li>share as much as you can about your hardware, such as its SDK, drivers and documentation;</li>
<li>provide physical calibration targets, such as AprilTags or a checkerboard;</li>
<li>watch the robot while it moves and be ready to stop it, to keep everyone safe.</li>
</ul>
</li>
<li><b>Tested embodiments.</b> The current workflow has been tested on fixed-base manipulators, wheeled mobile manipulators and quadruped loco-manipulators. Other embodiments may need extra work, and contributions that extend support are welcome.</li>
</ul>
</div>

## Onboarding

Start from a workspace and describe the hardware, how it connects, and what you want done:

```text
/onboarding Set up my robot arm, gripper, and overhead camera to pick objects from the table.
```

Onboarding runs as an interview. The agent:

1. **Looks before asking.** It checks existing device profiles, installed ROS packages and SDKs, local models and any prepared simulator files.
2. **Asks for what's missing.** Questions come in one batch, each with an "unknown" option. Facts nobody knows stay marked `???` instead of being guessed.
3. **Plans the work.** It records a plan in `.kinex/setup/plan.json`: which devices are needed, how they attach to each other, and which steps the task depends on.
4. **Prepares devices.** For each device it picks a guide, writes a driver and a profile, and leaves the device unloaded.
5. **Brings them up and checks them.** Once the devices are loaded (with `/load`, or by the agent with your permission), it runs reads and checks that matter for the task and keeps the results as evidence.
6. **Calibrates if the task needs it.** See [Calibration](#calibration) below.

Run `/onboarding` without a task to just prepare the device inventory; the agent then suggests next steps instead of measuring anything. Running it again with a new objective reuses everything already established and only revisits what the new task changes.

### One device at a time

To add a single device instead of a whole robot, use `/register`:

```text
/register rgbd
/register grounding-dino
```

The agent follows the built-in `setup-device` skill: choose a guide, set up a driver, write an unloaded profile and verify the interface. `/unregister <device>` unloads a device and, after you confirm, deletes its profile, driver and files.

## Calibration

Calibration pins down the physical facts a task depends on but that Kinex can't know in advance: a camera's intrinsics, where a camera sits relative to an arm, the tool-tip offset, joint limits, how two arms relate to each other. Describe what you want calibrated, or leave it blank and the agent picks up the current task:

```text
/calibrate camera-to-arm transform for picking
/calibrate
```

A calibration follows the same loop every time:

1. **Plan.** The agent reuses facts that are already known (from the manufacturer, a robot model or the simulator) and picks a procedure for whatever is still missing.
2. **Sample.** It moves the robot or asks you to, and captures measurements: images of a calibration board, joint readings, contact points. Each sample is saved as evidence under `.kinex/calib/`.
3. **Compute.** A built-in solver turns the samples into a result and checks its quality.
4. **Apply.** If the result is good enough, the agent writes it into the device's profile and marks that step of the plan done. If not, the agent tells you why and writes nothing, unless you choose to keep the approximate result; the failed quality check is then recorded with it.

When something physical changes, such as a camera being remounted, ask the agent to reassess and it will redo the affected calibration.

### Bundled calibration skills

| Skill | What it determines |
| --- | --- |
| `calibrate-camera-intrinsics` | A camera's lens and image geometry |
| `calibrate-camera-extrinsics` | Where a camera is mounted, on an arm or in the scene |
| `calibrate-tcp-offset` | The position of the tool tip relative to the arm's flange |
| `calibrate-fixed-arm-mount` | Where an arm is mounted relative to its parent, such as a table, mobile base or torso |
| `calibrate-dual-arm` | How two arms are positioned relative to each other |
| `calibrate-joint-range` | Joint limits, from the robot model or measurements |
| `calibrate-world-geometry` | Measured geometry of the surrounding environment |
| `verify-base-interface`, `verify-base-motion`, `verify-base-posture` | That a mobile or legged base behaves as declared |

You can add your own calibration skills like any other [skill](/docs/tools-and-skills/#discovery).

### Calibration in practice

These recordings show Kinex calibrating a simulated YAM dual-arm robot in Isaac Lab, through [RoboEnv](/docs/simulators/). Each plays at 5× speed.

<figure>
  <video src="/video/calib-wrist-cameras.mp4" poster="/video/calib-wrist-cameras.jpg" controls muted playsinline preload="none"></video>
  <figcaption><b>Wrist cameras.</b> Each arm moves its wrist camera around a fixed calibration board on the table to find where the camera sits on the flange (<code>calibrate-camera-extrinsics</code>).</figcaption>
</figure>

<figure>
  <video src="/video/calib-overhead-camera.mp4" poster="/video/calib-overhead-camera.jpg" controls muted playsinline preload="none"></video>
  <figcaption><b>Overhead camera.</b> The left arm holds a calibration board up to the fixed overhead camera in several poses to find the camera's position in the scene (<code>calibrate-camera-extrinsics</code>).</figcaption>
</figure>

<figure>
  <video src="/video/calib-dual-arm.mp4" poster="/video/calib-dual-arm.jpg" controls muted playsinline preload="none"></video>
  <figcaption><b>Dual arm.</b> Both arms touch the same set of reference points on the table, which lets the agent work out where the right arm's base is relative to the left (<code>calibrate-dual-arm</code>).</figcaption>
</figure>

## All set!

You're ready to go. Load your devices with `/load all`, check them with `/ping all`, and give Kinex its first task in plain language.
