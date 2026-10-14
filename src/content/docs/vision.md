---
title: Using vision models as tools
description: Register a vision model such as SAM3 as a device, locate objects in 3D with locate_object_3d, and combine perception, motion and observations with Python exec.
group: Guides
order: 50
label: Using vision models as tools
sources: ["docs/devices.md", "packages/core/assets/builtin/device/sam3/DEVICE.md", "packages/core/assets/builtin/device/grounding-dino/DEVICE.md", "packages/core/assets/builtin/tool/locate-object-3d/tool.yaml", "packages/core/README.md", "packages/core/assets/builtin/tool/relative-pose/tool.yaml"]
---

Vision models answer questions like "where is the red mug?" by finding objects in camera images. In Kinex, a vision model is not the agent; it's a tool the agent uses. The agent decides what to look for, which camera to use, and what to do with the answer.

This takes three pieces:

1. **The vision model becomes a device.** It's registered like a camera or an arm, as a `segmentation` or `detection` device with a `detect` operation.
2. **`locate_object_3d` uses it once.** It takes a camera image, asks the model to find the object, and turns the result into a 3D position.
3. **Python `exec` combines perception and action.** It converts the position for the arm, commands motion and returns fresh observations for the agent to check.

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

## 3. Combine perception and motion with `exec`

Use a Python script to locate the mug, transform its position and command an approach. This example assumes the arm's base Z axis points up and quaternion `[1, 0, 0, 0]` points its controlled tool frame down. Review that orientation, the clearance and the full path for your setup before motion.

```python
from kinex import call, device, finish, stop_owned

try:
    initial = device("arm")
    if initial["faults"]:
        raise RuntimeError(str(initial["faults"]))
    found = call("locate_object_3d", camera="wrist_cam", model="sam3",
                 prompt="red mug")
    x, y, z = found["point"]
    mug = call("relative_pose",
               child={"frame": found["frame"], "pose": [x, y, z, 0, 0, 0, 1]},
               parent={"frame": "arm"})["pose"]
    target = [mug[0], mug[1], mug[2] + 0.10, 1, 0, 0, 0]
    motion = call("servo", device="arm", pose=target)
    # Servo waited its planned duration; inspect measured state next.
    feedback = device("arm")
    if feedback["faults"]:
        raise RuntimeError(str(feedback["faults"]))
    if feedback["timestamp"] <= initial["timestamp"]:
        raise RuntimeError("fresh arm feedback unavailable")
finally:
    stop_owned()

frame = device("wrist_cam", args={"output": "file"})
finish({"target": target, "motion": motion, "feedback": feedback,
        "reason": "inspection required", "camera": "wrist_cam",
        "timestamp": frame["timestamp"]}, file=frame["file"])
```

This commands an approach and returns evidence; it does not claim the arm arrived or the mug was grasped. The agent checks measured state and the new image before continuing. For a numerical arrival check, use the bounded [feedback-control example](/docs/custom-tools/#feedback-control) with task-appropriate tolerances. For stability, also check fresh velocity feedback or a sequence of fresh position samples.

If the mug cannot be found, `locate_object_3d` raises an error before `servo` runs. When the next decision depends on confirming the detection visually, split the operation: return its overlay first, let the agent inspect it, then command motion. Images obtained inside Python must be returned through `finish(..., file=...)`; printing their paths does not display them.

For moving targets, implement a bounded Python loop that re-detects, transforms, commands and checks feedback. Use `block=False` with `servo` and an explicit `device("world", "wait", {"duration_s": interval_s})` between observations. Check faults, stale samples and elapsed time, and call `stop_owned()` when leaving the loop. The old `closed_loop` and `settled` built-ins are no longer provided.

The same pattern runs a policy model instead of a vision model; see [Using VLAs as tools](/docs/vla/).

## Bring your own model

To use a vision model that isn't built in, register it from a type template and describe it to the agent:

```text
/register segmentation my-segmenter served at http://gpu-box:8000, API key in SEG_API_KEY
```

As long as it answers `detect` in the standard form, with boxes and masks in the original image's pixels, `locate_object_3d` and every loop built on it work unchanged.
