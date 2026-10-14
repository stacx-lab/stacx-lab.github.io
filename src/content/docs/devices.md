---
title: Devices
description: Device types, profiles, drivers, lifecycle, frames and the world clock.
group: Concepts
order: 20
sources: ["docs/devices.md", "docs/commands.md", "packages/core/README.md", "packages/core/src/commands.ts"]
---

Kinex treats a robot as a collection of independent devices rather than one monolithic interface: a mobile base, arms, grippers and cameras. The agent coordinates them through tools and code for each task, adapting the workflow to the capabilities available. For example, if a camera is missing, it can use another viewpoint where one is available.

A device is anything the agent can read from or command: a piece of hardware, part of a simulator, or a service such as a detection model. Every device has three parts:

- a **type**, which defines its operations and data conventions;
- a **profile**, which records how to reach it and its specifications;
- a **driver**, which talks to the actual SDK, simulator or service.

Real and simulated devices use the same types, so the agent works with both the same way.

## Types

A type describes what a device can do, not who made it. A robot is usually several devices: an arm, a gripper, a few cameras.

| Type | What it provides |
| --- | --- |
| `joint` | Joint-position control and feedback, plus forward/inverse kinematics if the profile declares them |
| `dexterous_hand` | Joint-position control, with optional finger geometry |
| `gripper` | Numeric commands for opening and closing a gripper |
| `suction` | Numeric commands for turning suction on and off |
| `velocity` | Velocity commands on named axes, with optional posture control (for example, a mobile base) |
| `legged_base` | High-level modes from the robot's SDK, such as stand, crouch and drive |
| `rgb` | Color images |
| `rgbd` | Color images and depth |
| `imu` | Inertial readings |
| `force_torque` | Force or torque readings, or both |
| `model` | Inference operations whose inputs and outputs are declared in the profile |
| `detection` | Find objects from an image and a text prompt (`detect`) |
| `segmentation` | Find objects from an image and a text prompt (`detect`), with a mask for each |
| `world` | The environment clock (`read`, `wait`), with optional scene geometry |
| `other` | Anything that doesn't fit the types above |

Some types can stand in for others: an `rgbd` camera works wherever an `rgb` camera is required, and a `segmentation` model works wherever a `detection` model is.

## Profiles

Each workspace keeps its devices under `.kinex/`:

```text
.kinex/
├── workspace.yaml              # the robot as a whole: identity, simulator details, safety settings
└── devices/<name>/
    ├── profile.yaml            # this device's profile
    └── driver.py               # its driver (or a pinned ROS-generated driver)
```

A profile contains:

| Field | What it holds |
| --- | --- |
| `name`, `type` | The device's name and the type it follows |
| `loaded` | Whether the device should be connected. This records your intent; it doesn't mean the device is ready. |
| `access` | How to connect, and how to run the driver (`entry`, `interpreter`, `actions`, `persistent`, `timeout_s`) |
| `intrinsics` | Facts about the device itself, such as joint models, camera parameters or inference operations |
| `extrinsics` | Where the device is mounted relative to something else (not used for `world` or models) |

A value of `???` means the fact is still unknown, and `needs_calibration` marks a value that calibration still has to fill in. Change profiles through the agent's `profile_write` tool rather than editing the YAML by hand during a session.

## Drivers

A driver should expose only the device's basic, atomic operations, such as reading its state or sending one command. Higher-level behavior like planning a trajectory, running a feedback loop or chaining several calls belongs in tools and skills, which build on those operations.

Every driver supports `load`, `unload`, `status` and `read`. Actuators also support `write` and `stop`. Arms and hands can provide `fk` and `ik` if their profile declares them, `world` adds `wait`, and models add their own inference operations. A driver can run once per call, or stay running as a persistent process (started with `--serve`) that exchanges JSON lines over stdin and stdout and writes diagnostics to stderr.

## Connecting, stopping and disconnecting

```text
/devices            # list devices and whether each should be loaded
/load arm           # connect and wait until the driver is ready
/ping arm           # check status without starting anything
/stop arm           # stop its motion right away (or /stop for every device)
/unload arm         # disconnect and release its resources
/unregister arm     # after confirmation, unload and delete the profile, driver and files
```

To restart a device, run `/unload arm` and then `/load arm` (or use `all`). If a device's driver fails, Kinex doesn't restart it automatically; reads and writes report the error until you run `/unload` and `/load` again.

`/stop` skips the approval prompt and also cancels the agent's current response. What stopping means depends on the device, and each driver declares its own stop behavior. For example, an arm drops its queued motion, a mobile base comes to a halt, and a gripper keeps holding whatever it has grasped rather than opening.

## Reading devices and camera images

`device` calls one device; `devices` calls several concurrently and returns results in input order. Batch entries use `deviceID`, `action` and `args`. Each result has its own `ok` status and data or error; the batch is neither atomic nor a simultaneous sample. Successful camera images survive a partial failure. The agent-facing batch is marked as an error only when every call fails.

Direct camera calls through `device` or `devices` attach RGB images automatically. Inside Python, camera reads default to NumPy arrays for computation and do not display images to the agent. Request `output="file"`, then return selected paths with `finish(result, file=[...])`. Keep camera names and acquisition timestamps with the images; returning several together does not synchronize their clocks. See [Returning camera observations](/docs/custom-tools/#returning-camera-observations).

## Spatial and temporal relationships

### Space: frames and extrinsics

Every device has its own coordinate frame, and some devices have more than one. An arm, for instance, has frames for its base, each link and its flange, computed from its joint model. A device's **extrinsics** say where it is mounted relative to another device's frame. A wrist camera mounted on an arm's flange looks like this:

```yaml
extrinsics:
  mount:
    parent: arm              # the device it is attached to
    parent_frame: flange     # which frame on that device
    translation_m: [0.04, 0, 0.02]
    rotation_xyzw: [0, 0, 0, 1]
```

Linking devices this way builds a tree of frames. As the arm moves, Kinex follows the chain through the arm's measured joints, so it can work out where the camera is at any moment. That is how `relative_pose` turns a point that `locate_object_3d` finds in the camera's frame into a target in the arm's frame.

Some rules for frames:

- Poses are written as `[x, y, z, qx, qy, qz, qw]`: position in metres and orientation as a unit quaternion. Cameras use optical axes (X right, Y down, Z forward).
- Unknown values stay `???` until they're measured. Filling them in is what calibration does (see [Onboarding & calibration](/docs/onboarding/#calibration)).
- There is not always a single tree. If two frames aren't linked, Kinex treats their relationship as unknown rather than assuming they line up.
- A shared world frame is optional. Mobile and legged bases don't know their position in the world, so relating them to the world needs an explicit estimate.

### Time: the world clock

Each device timestamps its readings with its own clock, in seconds. These clocks are not synchronized with each other automatically.

The `world` device provides the clock the task runs on. On real hardware it follows real (monotonic) time; in a simulator, the simulator's driver supplies its own clock.

- `world.read` returns the current time `time_s`, and may also report an episode budget as `budget: {used_s, max_s}`. Kinex shows the budget but doesn't enforce it.
- `world.wait({duration_s})` lets time pass and returns the new `time_s` and how long it actually waited (`waited_s`).

Simulators run in one of two modes:

- **Realtime:** the simulation keeps running on its own, including while the agent is thinking.
- **Stepped:** simulated time only moves forward during `world.wait`. Reads never advance it, and a host `sleep` doesn't either.

So in a stepped simulator, commanding a motion and then reading the result isn't enough on its own: call `world.wait` in between to let the motion happen. Blocking `servo` already waits its planned duration on a loaded world clock, so do not wait that duration twice. It does not verify arrival. With `block=False`, or asynchronous device writes and `run_policy`, scripts must wait explicitly and then check fresh feedback.
