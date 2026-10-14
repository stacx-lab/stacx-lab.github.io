---
title: Working with the agent
description: Choose a model, talk to the agent, set how much it asks for approval, and manage conversations, compaction and sessions.
group: Guides
order: 10
label: Working with the agent
sources: ["README.md", "docs/agent-integration.md", "src/application.ts", "src/auth.ts", "src/arguments.ts", "src/sessions.ts", "src/settings.ts", "src/export.ts", "src/resume-hint.ts", "src/integration/interaction.ts", "src/integration/extension.ts"]
---

Kinex is built on the [Pi](https://pi.dev) coding agent (`@earendil-works/pi-coding-agent`, bundled at version 1.2.0, so there's nothing extra to install). Pi provides the agent itself: the model connection, the conversation loop, the terminal UI, sessions, compaction and the everyday coding tools (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`). Kinex adds the robotics on top: devices, robotics tools and skills, permissions and recording.

Apart from approvals and devices, everything on this page works the way it does in Pi. If you've used Pi or a similar coding agent before, it will feel familiar. For more detail, see [Pi's documentation](https://github.com/earendil-works/pi/tree/v1.2.0/packages/coding-agent/docs).

## Choosing a model

The agent model is the LLM that reads your requests and decides what to do. It's separate from the perception and policy models your robot uses, which are [devices](/docs/devices/) (see [Using vision models as tools](/docs/vision/) and [Using VLAs as tools](/docs/vla/)). Slash commands like `/ping` don't need a model at all.

```text
/login              # connect a provider, with an OAuth subscription or an API key (or set one of the API-key environment variables Pi recognizes)
/model              # pick a model
/thinking high      # set reasoning effort
```

You can also choose from the shell:

```sh
kinex --model provider/model
kinex --model sonnet --provider anthropic     # match a model name within one provider
kinex --thinking xhigh                        # off, minimal, low, medium, high, xhigh or max
```

### Local or custom models

To use a model you host yourself, add it to `~/.config/kinex/agent/models.json`:

```json
{
  "providers": {
    "local": {
      "api": "openai-completions",
      "baseUrl": "http://localhost:11434/v1",
      "apiKey": "local",
      "models": [{ "id": "your-model-name" }]
    }
  }
}
```

Start the model server, then choose `local/your-model-name` with `/model`. See Pi's [custom provider docs](https://github.com/earendil-works/pi/blob/v1.2.0/packages/coding-agent/docs/models.md) for all options.

### Where credentials are kept

Credentials live in `~/.local/share/kinex/agent/auth.json`, with a link at `~/.config/kinex/agent/auth.json` so every part of Kinex shares one login. If that location already holds different credentials, Kinex stops with `AuthPathConflict` rather than overwrite them; merge the two files and restart. Keep agent credentials out of device profiles. Model devices read their own keys from environment variables.

## Talking to the agent

Type a request and press Enter. While the agent is working, you can keep talking to it:

| Key | Effect |
| --- | --- |
| Type and press Enter | Steer the current turn with new instructions |
| **Alt+Enter** | Queue a follow-up for when the agent finishes |
| **Escape** | Interrupt the agent |
| **Ctrl+O** | Expand tool calls to see exactly what was run and returned |

A few other commands help day to day: `/copy` copies the agent's last reply, `/settings` opens preferences and `/hotkeys` lists every shortcut. `/quit` exits. Escape only stops the agent's response; to stop the robot as well, use `/stop`.

Kinex also bundles two Pi extensions: [pi-web-search](https://www.npmjs.com/package/pi-web-search), which lets the agent search the web, and [pi-btw](https://www.npmjs.com/package/pi-btw), for side conversations that don't interrupt the main one. Side conversations use Pi's regular coding tools only, without your devices or Kinex's approval checks. You can add more Pi packages; see [Plugin systems](/docs/plugins/).

## Approval modes

Before the agent runs a tool, such as reading a device, moving the robot or running a shell command, Kinex checks whether it needs your approval. The approval mode sets how much it asks:

| Mode | The agent's tool calls | The agent's questions to you |
| --- | --- | --- |
| `ask` (default) | Follow your permission rules, and ask you when a rule says to | You answer them |
| `auto` | All allowed, even ones your rules deny | You answer them |
| `yolo` | All allowed | Answered automatically with "keep going" |

Switch with `/mode` (or `/mode auto`), or start in a mode with `kinex --auto` or `kinex --yolo`. The current mode is shown in the footer.

When Kinex asks, you can **allow once**, **allow for the rest of the session**, or **deny**. Denying stops the rest of that turn, so related calls don't run without you. Switching mode clears the approvals you've granted for the session.

In scripted runs without a terminal, nobody is there to answer, so in `ask` mode anything that would prompt is denied and the agent's questions are answered from the evidence it already has. See [Kinex runtime](/docs/runtime/#permissions) for what each permission covers and how to set rules.

## Sessions

A **session** is one conversation: your messages, the agent's replies and every tool call. It's separate from the **workspace**, the `.kinex/` folder that holds your devices, tools, skills and recordings. Switching sessions never changes the workspace, and vice versa.

Each session is saved automatically. When you quit, Kinex prints the command to come back to it. To return later:

```sh
kinex --continue              # the latest session in this workspace (-c)
kinex --resume                # choose from a list (-r)
kinex --session 3f2a          # a specific session, by ID or the start of one
```

Inside Kinex, `/new` starts a fresh session and `/resume` switches to another. Sessions are stored as JSONL files under `~/.local/share/kinex/agent/sessions/`, grouped by workspace.

### Branching

Pi keeps each session as a tree, so you can go back and try something different without losing what came before:

| Command | Effect |
| --- | --- |
| `/tree` | Browse the session's branches and jump to any point |
| `/fork` | Start a new session from an earlier message |
| `/clone` | Copy the session as it is now |
| `/name [name]` | Give the session a name |

### What happens to your devices

Changing session within the same workspace (`/new`, `/resume`, `/fork`) keeps your devices connected, so you don't have to load them again. It does cancel any call still running, reset the permissions you granted for the session and finish any active recording. Quitting Kinex or switching to another workspace disconnects the devices Kinex started; services you started yourself, like a simulator, keep running.

## Context and compaction

Long conversations eventually fill the model's context window. Compaction summarizes the conversation so far so you can keep going:

```text
/compact                                      # summarize now
/compact keep the calibration results in detail   # tell it what to preserve
```

Kinex makes sure compaction doesn't lose track of the robot. Before every request it gives the agent a fresh picture of the workspace: loaded devices, how to use them, and the Python environment. That picture is rebuilt in full after compaction. The robotics guidance asks the agent to avoid unnecessary tool calls and motion, account for intended contact, and check the full path for unintended collisions. Command acceptance or arrival alone does not establish task success. Old observations in the history are still just history, though. When the current state matters, the agent should read the device again.

The footer shows how long you've been actively working in the session, not counting idle time.

## Exporting a conversation

To save or share a conversation:

```text
/export [path]        # save this session as HTML or JSONL
```

```sh
kinex --export session.jsonl [output.html]    # convert a saved session, no model needed
```

Exports include file paths, tool output and images, so review them before sharing. To capture what the robot saw and did, use [Recording](/docs/recording/) instead.
