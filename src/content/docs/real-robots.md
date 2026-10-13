---
title: Working with real robots
description: Onboard hardware for a concrete task with /onboarding and /register.
group: Get started
order: 30
label: Real robots
sources: ["README.md", "packages/setup/README.md", "packages/setup/src/workflows/onboarding.txt", "packages/core/assets/builtin/skill/setup-device/SKILL.md", "docs/setup.md"]
---

Kinex drives real hardware through the same device interface it uses for simulators. You describe your robot and what you want it to do; the agent writes the device profiles and drivers, brings the hardware up and checks it, calibrating only what the task needs. Supported embodiments include arms, lifts, mobile bases, quadrupeds, grippers, suction, dexterous hands, cameras, IMUs and F/T sensors (see [Devices](/docs/devices/)).

Assumes Kinex is installed (see [Install and run](/docs/#install-and-run)).

## 1. Start Kinex in a fresh workspace

```sh
mkdir -p robot-workspace
cd robot-workspace
kinex
```

If you haven't yet, connect a model with `/login` and `/model`.

## 2. Onboard your robot

Describe the hardware, how it connects, and the task:

```text
/onboarding Set up my robot arm, gripper, and overhead camera to pick objects from the table.
```

Onboarding is an interview. The agent inspects what is already there, asks only for missing facts, and records a plan in `.kinex/setup/plan.json`. It then prepares profiles and drivers, loads the devices and verifies them, covering only what this task needs. Unknowns stay `???`; nothing is invented.

You can also register devices one at a time with `/register <type-or-template>`:

```text
/register rgbd
/register grounding-dino
```

Each sets up a driver and writes an unloaded profile, validating it without touching the hardware; run `/load` to bring it up. ROS hardware is routed through `onboard-ros2` automatically (see [ROS 2 hardware](/docs/onboarding/#ros-2-hardware)).

## 3. Calibrate

Calibration pins down the physical facts the task depends on but the agent can't know yet, such as camera intrinsics, where a camera sits relative to the arm (extrinsics), the tool-tip (TCP) offset, or joint limits. It is handled by Kinex's calibration skills. Describe what you want calibrated, or leave it blank:

```text
/calibrate camera-to-arm transform for picking
/calibrate
```

The agent works out what needs calibrating and which procedure to follow, guides you through collecting samples, and writes the result into the device profile. See [Onboarding & calibration](/docs/onboarding/#calibration) for the bundled procedures.

## 4. Bring it up and give a task

```text
/devices
/load all
/ping all
```

Then give the task in plain language. Useful during work:

| Command | Effect |
| --- | --- |
| `/stop [device]` | Cancel the response, stop actuators in their stop scope |
| `/unload <device>` | Release a device |
| `/unregister <device>` | Confirm, then delete its profile, driver and files |
