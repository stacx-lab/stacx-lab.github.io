---
title: Using vision models as tools
description: Register a vision model such as SAM3 as a device, locate objects in 3D with locate_object_3d, and act on them with closed_loop.
group: Guides
order: 50
label: Using vision models as tools
sources: ["docs/devices.md", "packages/core/assets/builtin/device/sam3/DEVICE.md", "packages/core/assets/builtin/device/grounding-dino/DEVICE.md", "packages/core/assets/builtin/tool/locate-object-3d/tool.yaml", "packages/core/assets/builtin/tool/closed-loop/tool.yaml", "packages/core/assets/builtin/tool/relative-pose/tool.yaml"]
---

Vision models answer questions like "where is the red mug?" by finding objects in camera images. In Kinex, a vision model is not the agent; it's a tool the agent uses. The agent decides what to look for, which camera to use, and what to do with the answer.

This takes three pieces:

1. **The vision model becomes a device.** It's registered like a camera or an arm, as a `segmentation` or `detection` device with a `detect` operation.
2. **`locate_object_3d` uses it once.** It takes a camera image, asks the model to find the object, and turns the result into a 3D position.
3. **`closed_loop` repeats it.** It keeps looking, converting the position for the arm and moving, until the arm has arrived.

This page uses [SAM3](https://huggingface.co/facebook/sam3), an open-vocabulary segmentation model, as the example. [Grounding DINO](https://huggingface.co/IDEA-Research/grounding-dino-tiny) works the same way and is also built in.

## 1. Register the vision model as a device

Let the agent set it up:

```text
/register sam3
```

The agent follows the built-in `setup-device` skill and SAM3's own setup guide. It asks whether to run on a GPU or the CPU, checks your Hugging Face access, installs the model into its own environment inside `.kinex/devices/sam3/`, downloads the weights, and writes a driver and a profile. The device is left unloaded. Loading it puts the model on the GPU, so load it only when you need it:

```text
/load sam3
```

SAM3's weights are gated on Hugging Face. Request access at [facebook/sam3](https://huggingface.co/facebook/sam3) and make a token available (for example as `HF_TOKEN`) before registering.

The result is an ordinary device. Its profile records where the model runs and what it can do:

```yaml
name: sam3
type: segmentation
access:
  connection: {kind: process, compute: {kind: cuda, index: 0}}
intrinsics:
  family: sam3
  operations:
    - segment_point   # a clicked point → masks
                      # detect (text prompt → boxes, scores, labels and masks)
                      # comes with the segmentation type
```

*(Abridged; the real profile spells out each operation as JSON Schema.)*

Every `segmentation` and `detection` device answers the same `detect` call: give it an image and a text prompt, and it returns the matching objects. Each object has a bounding box in image pixels, a score and a label; segmentation models also return a mask. It may also return an overlay image showing what it found; SAM3 always does. The model only looks at the image you give it. It never takes a picture itself.

## 2. Locate an object with `locate_object_3d`

`locate_object_3d` connects the vision model to a camera. It reads the camera, asks the model to find the object, then uses the depth image to work out how far away it is:

```json
{
  "camera": "wrist_cam",
  "model": "sam3",
  "prompt": "red mug"
}
```

- **`camera`** must be calibrated (see [Onboarding & calibration](/docs/onboarding/#calibration)). An RGB-D camera supplies depth itself. For a plain RGB camera, pass a known distance as `depth`.
- **`model`** is any `detection` or `segmentation` device.
- **`prompt`** describes the object in plain words.
- Optional: **`min_score`** ignores weak matches (default 0.25), and **`instance`** picks another match when there are several (0 is the best).

The result is a point in metres, in the camera's frame (X right, Y down, Z forward). It comes with the detection score, how the depth was measured and the overlay image, which the agent can look at to check it found the right thing:

```json
{
  "frame": "wrist_cam",
  "point": [0.04, -0.02, 0.31],
  "label": "red mug",
  "detection_score": 0.91,
  "reference": "visible_surface"
}
```

With a segmentation model like SAM3, depth is measured inside the object's mask, so the point lies on the object's visible surface. A detection-only model gives just a box, so depth comes from the central half of the box and may include some background.

The point is in the camera's frame. To use it with the arm, convert it with `relative_pose`, which works through the camera's mount (see [Spatial relationships](/docs/runtime/#spatial-relationships)).

## 3. Close the loop with `closed_loop`

One call tells you where the object is right now. To reach it, you look, move a little, look again and repeat, so that small errors and moving objects are corrected along the way. `closed_loop` runs that cycle for you:

```text
perceive → process → control → wait → until
   ↑                                    │
   └──────────── not done ──────────────┘
```

| Stage | Role | For a vision model |
| --- | --- | --- |
| `perceive` | Gather fresh observations | `locate_object_3d` finds the mug |
| `process` | Turn observations into the next command's arguments | Convert the point into a target pose for the arm |
| `control` | Act | `servo` moves the arm toward the target |
| *wait* | Let the world advance by `wait_s` | Let the arm move for a moment |
| `until` | Decide whether to stop | `settled` checks the arm has arrived and stopped |

Each stage is either a tool or a short piece of Python. Here is a loop that moves the gripper to 10 cm above the mug, pointing down:

```python
from kinex import call

call("closed_loop", world="world", wait_s=0.2,
    perceive={"tool": "locate_object_3d",
              "args": {"camera": "wrist_cam", "model": "sam3", "prompt": "red mug"}},
    process={"python": """
from kinex import call
def main(observation):
    x, y, z = observation["point"]
    mug = call("relative_pose", child={"frame": observation["frame"], "pose": [x, y, z, 0, 0, 0, 1]},
               parent={"frame": "arm"})["pose"]
    return {"pose": [mug[0], mug[1], mug[2] + 0.10, 1, 0, 0, 0]}
"""},
    control={"tool": "servo", "args": {"device": "arm", "block": False}},
    until={"tool": "settled", "args": {"timeout_s": 15}})
```

Each round finds the mug again, works out where it is relative to the arm's base, sets a target 10 cm above it with the gripper pointing down, and lets the arm move toward it for 0.2 seconds of world time. Then it looks again. The loop ends when `settled` sees the arm has reached the target and stopped, or after 15 seconds. `settled` restarts its check whenever the target changes, so if the detected position jitters from round to round, the loop may run until the timeout.

You rarely write this by hand. Ask the agent to "move the gripper above the red mug", and it builds the loop, checks the overlay images and adjusts.

A few things the loop handles for you:

- **Lost objects.** If the mug can't be found, `locate_object_3d` reports an error, and the loop stops the arm and ends with that error instead of moving blindly.
- **Replanning.** A new `servo` target replaces the previous one, so `wait_s` sets how often the arm corrects course. Use `"block": false` so `servo` returns immediately and the loop keeps the rhythm.
- **Timing.** Waits use the `world` clock, so the loop behaves the same in a stepped simulator and on real hardware.
- **Stopping safely.** On an error, a cancel or the end of the loop, `closed_loop` stops the motion it started. When it ends normally, it reports why: `settled` succeeded, a timeout, the round limit, or too many rounds without a target.

The same pattern runs a policy model instead of a vision model; see [Using VLAs as tools](/docs/vla/).

## Bring your own model

To use a vision model that isn't built in, register it from a type template and describe it to the agent:

```text
/register segmentation my-segmenter served at http://gpu-box:8000, API key in SEG_API_KEY
```

As long as it answers `detect` in the standard form, with boxes and masks in the original image's pixels, `locate_object_3d` and every loop built on it work unchanged.
