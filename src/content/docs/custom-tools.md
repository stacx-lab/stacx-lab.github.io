---
title: Custom tools & skills
label: Custom tools & skills
description: Run Python against your devices, and extend Kinex with your own tools and skills.
group: Guides
order: 30
sources: ["packages/core/README.md", "docs/tools-and-skills.md", "docs/overview.md", "packages/core/src/tool/exec.txt"]
---

There are three ways to extend what Kinex can do, from quickest to most reusable:

- **Run a Python script** for a one-off job, like inspecting a device or trying out a motion.
- **Add a tool** when an operation is worth reusing: the agent can then call it by name like any built-in tool.
- **Add a skill** to teach the agent how to approach a kind of task.

The agent can write these for you: ask it to "turn that into a tool" or "write a skill for this". You can also write them by hand. Either way they're files in your workspace, so they're easy to review, edit and share.

## Running Python

The agent runs Python through the `exec` tool. Supply exactly one of `python` (source) or `file` (a script path). No manifest, `main()` function or `kind` is needed. Optional `description` gives the invocation a short display label, such as `inspect arm state`.

A snippet that reads the arm and a camera together:

```python
from kinex import devices

for result in devices(calls=[{"deviceID": "arm"}, {"deviceID": "camera"}])["results"]:
    print(result["deviceID"], result["ok"])
```

Or an existing script, with arguments:

```json
{"file": "scripts/inspect.py", "argv": ["--samples", "10"], "args": {"device": "arm"}}
```

Each invocation runs in a fresh process from the runtime's working directory. `args` is available through `kinex.args()`; `argv` supplies `sys.argv[1:]`. Files support script-local imports and `__name__ == "__main__"`. Optional `interpreter` selects another Python executable.

The result contains `exit_code`, bounded combined stdout/stderr in `output` (up to the last 16 KB), and `result` (normally `null`). `finish(value)` supplies a structured result; it can also attach one or more images. Scripts time out after 120 wall-clock seconds unless given a different `timeout_s`; composed tools also enforce their own timeouts within the remaining time.

A few things to know:

- **One approval covers the script.** You approve `exec` once, and that covers every device call the script makes.
- **Scripts can't load or unload devices** or start recordings; those stay with you and the agent.
- **Choose when motion stops.** On failure, timeout or cancellation, Kinex attempts to stop motion still owned by the script. Cleanup failures are logged while the original error is returned. Successful scripts can leave motion running; call `stop_owned()` when the exit condition requires a stop, or use `/stop` yourself.
- **Inspect batch errors.** `devices()` returns per-entry results. An entry with `ok: false` does not raise an exception by itself; check it before continuing control.

### The `kinex` library

Scripts and tools use the `kinex` Python library to talk to the runtime:

| Function | Does |
| --- | --- |
| `device(deviceID, action="read", args=None)` | Call one device. Camera reads return NumPy arrays. |
| `devices(calls)` | Call several devices at once |
| `call(tool, **args)` | Compose a Python tool or `device`/`devices` using keyword arguments; host shell and file tools are outside this API |
| `profile(name)` | Read a device's profile, including its calibration |
| `robot()` | Read the workspace description |
| `args()` | The arguments passed to the script or tool |
| `finish(result, file=None)` | Return JSON, optionally with one image path or an ordered list of paths |
| `stop_owned()` | Stop motion still owned by this invocation and surface cleanup errors |
| `fail(message)` | Stop with an error the agent will see |

```python
from kinex import call, device

state = device("arm")
call("servo", device="arm", joints=[0, -0.5, 0, 1.2, 0, 0.8, 0], block=False)
```

Pass tool parameters as keywords: `call("servo", **params)`, not `call("servo", params)`. In contrast, `device("world", "wait", {"duration_s": 0.1})` takes an argument dictionary. A failed call raises `kinex.RPCError`, which carries a `code` and `details`.

### Returning camera observations

Python camera reads default to arrays and do not attach images automatically. For an agent decision that needs visual input, request files and return them explicitly:

```python
from kinex import device, finish

observations = []
images = []
for camera in ["head_camera", "wrist_camera"]:
    frame = device(camera, args={"output": "file"})
    observations.append({"deviceID": camera, "timestamp": frame["timestamp"]})
    images.append(frame["file"])
finish({"observations": observations}, file=images)
```

`file` accepts one path or an ordered list. When attaching files, the result must be a JSON object (or omitted); Kinex includes the paths in its `file` field. Printing paths or returning base64 text does not attach images. Camera names and timestamps identify the separate observations.

### Feedback control

Use bounded Python loops in `exec` for control, measured feedback and task-specific stopping checks. The `closed_loop` and `settled` built-ins are no longer provided. For an arm with bounded revolute joints, the following script takes target `joints` and a positive `tolerance_rad` through exec's `args`:

```python
from kinex import args, call, device, finish, stop_owned

params = args()
try:
    initial = device("arm")
    if initial["faults"]:
        raise RuntimeError(str(initial["faults"]))
    previous_stamp = initial["timestamp"]
    motion = call("servo", device="arm", joints=params["joints"])
    # Blocking servo already waited the planned duration. Check fresh feedback.
    for _ in range(20):
        feedback = device("arm")
        if feedback["faults"]:
            raise RuntimeError(str(feedback["faults"]))
        if feedback["timestamp"] < previous_stamp:
            raise RuntimeError("device clock moved backwards")
        fresh = feedback["timestamp"] > previous_stamp
        previous_stamp = feedback["timestamp"]
        error = max(abs(q - goal) for q, goal in
                    zip(feedback["positions"], motion["joints"], strict=True))
        if fresh and error <= params["tolerance_rad"]:
            break
        device("world", "wait", {"duration_s": 0.1})
    else:
        raise TimeoutError("joint target not confirmed")
finally:
    stop_owned()

frame = device("wrist_camera", args={"output": "file"})
finish({"feedback": device("arm"), "camera": "wrist_camera",
        "timestamp": frame["timestamp"]}, file=frame["file"])
```

Adapt the names, units and tolerances to the workspace. Continuous joints need angular error modulo a full turn. Position agreement alone does not establish stability, grasp success or task completion; check the feedback the task needs. Missing feedback and faults must stop the loop.

For replanning during motion, use `block=False` and explicit world waits between observations. Blocking `servo` already waits its planned duration on a loaded world clock; waiting that duration again is unnecessary. When further motion depends on visual interpretation, return selected images to the agent before continuing. `stop_owned()` checks ownership before stopping, subject to the driver's declared physical stop scope.

### The Python environment

By default, scripts, tools and drivers run in one shared Python ≥ 3.11 environment per workspace, in `.kinex/python/`. A driver or tool can use its own interpreter when it needs isolated dependencies, as model devices often do. Kinex creates it with [uv](https://docs.astral.sh/uv/) the first time it's needed, and never touches your own Python projects. To add a package:

```sh
uv add --project .kinex/python opencv-python-headless
```

## Adding a tool

Turn something into a tool when you or the agent will want it again. A tool has a name, a description and declared inputs, so the agent can find it and call it correctly without re-reading any code.

To add a Python tool, create a folder under `.kinex/tools/` with two files. Here is a tool that estimates whether a closed gripper stopped on an object instead of closing all the way:

```text
.kinex/tools/grasp_check/
├── tool.yaml
└── tool.py
```

`tool.yaml` describes the tool to the agent:

```yaml
name: grasp_check
kind: perception        # required by the manifest schema
description: Estimate whether a closed gripper is holding an object, from its measured opening.
parameters:
  type: object
  properties:
    gripper: {type: string, description: "Gripper device name"}
    min_aperture: {type: number, default: 0.005}
  required: [gripper]
```

`tool.py` does the work, reading its inputs with `args()` and returning with `finish()`:

```python
from kinex import args, device, fail, finish

a = args()
aperture = device(a["gripper"])["aperture_m"]
if aperture is None:
    fail("this gripper doesn't report its opening")
finish({"holding": aperture > a.get("min_aperture", 0.005), "aperture_m": aperture})
```

That's all. Kinex picks up new and changed tools at the agent's next step, without a restart, so the agent can write a tool and use it in the same task. The quickest way to start is to copy one of the [built-in tools](https://github.com/stacx-lab/kinex/tree/main/packages/core/assets/builtin/tool) and adapt it.

You can also write tools in TypeScript or JavaScript: put a `.ts` or `.js` file directly in `.kinex/tools/` that exports a `description`, `parameters` (a [Zod](https://zod.dev) schema) and an `execute` function.

## Adding a skill

A skill is a written procedure: how to approach a kind of task, what to check, and what to watch out for. Add one when you find yourself giving the agent the same guidance again and again.

Create a folder under `.kinex/skills/` with a `SKILL.md`:

```markdown
---
name: pick-and-place
description: Pick an object from the table and place it in a target, using the wrist camera to locate both.
---

# Pick and place

1. Read the wrist camera and locate the object with `locate_object_3d`.
2. Convert its position into the arm's frame with `relative_pose`.
3. ...
```

The agent always sees each skill's name and description, and loads the full instructions only when a description matches the task. So write the description to say clearly *when* the skill applies. You can keep supporting material, such as reference notes or helper scripts, in the same folder and mention it in the instructions.

## Where to put them

Tools and skills in a project's `.kinex/` folder apply to that project. To make one available everywhere, put it in `~/.config/kinex/tools/` or `~/.config/kinex/skills/` instead. When two have the same name, the one closest to your project wins; see [Tools & skills](/docs/tools-and-skills/#discovery) for the details.

Custom tools are code that runs on your machine with access to your robot. Review them as you would any other code, especially ones written by the agent or shared by others.
