---
title: CLI reference
description: Every `kinex` shell command and option in v1.0.0.
group: Reference
order: 10
label: CLI
sources: ["src/cli.ts", "src/arguments.ts", "src/packages.ts", "docs/commands.md", "docs/distribution.md", "install.sh", "src/upgrade.ts"]
---

Kinex's command line follows the syntax of the Pi coding agent it's built on, with robotics options added and a few Pi options left out. For commands you type inside a session, see [Slash commands](/docs/slash-commands/).

## Commands

| Command | Does |
| --- | --- |
| `kinex ["prompt" ...]` | Start an interactive session, optionally sending prompts right away |
| `kinex run "prompt"` | Run one task without the TUI and print the final reply (same as `-p`) |
| `kinex --export <session.jsonl> [output.html]` | Turn a saved session into HTML, without starting a model |
| `kinex install <source> [-l]` | Install a Pi package (`npm:`, `git:` or a local path); `-l`/`--local` for this project only |
| `kinex remove <source> [-l\|--local]` | Remove a package (alias: `uninstall`) |
| `kinex list` | List installed and bundled packages |
| `kinex update` | Update Kinex itself (same as `--self`) |
| `kinex update --extensions` | Update installed packages, keeping version pins |
| `kinex update <source>` | Update one package |
| `kinex update --all` | Update Kinex, then all packages |

## Options

### Running

| Option | Does |
| --- | --- |
| `-p`, `--print` | Run without the TUI and print the final reply. Also implied when input or output isn't a terminal. |
| `--mode text\|json` | Print the final text (default), or stream every event as JSON lines. `json` implies `-p`. |

### Sessions

| Option | Does |
| --- | --- |
| `-c`, `--continue` | Continue the most recent session in this workspace |
| `-r`, `--resume` | Choose a saved session from a list (needs a terminal) |
| `--session <id\|path>` | Open a specific session, by ID, the start of an ID, or file path |

### Model

| Option | Does |
| --- | --- |
| `--model <pattern>` | Choose the model, as `provider/model` or a name to match |
| `--provider <name>` | Only match models from this provider (use with `--model`) |
| `--thinking <level>` | Reasoning effort: `off`, `minimal`, `low`, `medium`, `high`, `xhigh` or `max` |

### Approvals

| Option | Does |
| --- | --- |
| `--auto` | Allow all tool calls; the agent still asks you questions |
| `--yolo` | Allow all tool calls and answer the agent's questions automatically |

`--auto` and `--yolo` can't be combined. See [Approval modes](/docs/agent/#approval-modes).

### Recording

| Option | Does |
| --- | --- |
| `--record "arm=10 camera=2"` | Record these devices at these rates (Hz) during a `-p` run |
| `--enable-recording` | Let the agent start and stop recordings itself |

### Other

| Option | Does |
| --- | --- |
| `-h`, `--help` | Show help |
| `-v`, `--version` | Show the version |

## Input and prompts

- Text piped into `kinex` is added to the start of the first prompt.
- Put `--` before a prompt that starts with `-`, so it isn't read as an option.
- Unknown options are rejected. Pi's RPC mode, `@file` attachments and its advanced tool and resource flags aren't supported.

## Examples

```sh
kinex "Inspect the workspace"                           # start a session with a first prompt
kinex run "/ping arm"                                   # run a slash command and exit
kinex -p --mode json "Describe the scene" > events.jsonl
kinex -c --model provider/model                         # continue, with a different model
kinex -p --record "arm=10 camera=2" "Pick the red mug"  # scripted run, recorded
kinex --export session.jsonl out.html
kinex update --all
```

## Changed in 1.0.0

| Old | Use instead |
| --- | --- |
| `--seed "prompt"` | `kinex "prompt"` |
| `--json` | `--mode json` |
| `--effort` | `--thinking` |
| `kinex upgrade` | `kinex update`, or `kinex update --all` |

## Install and update

Install, or reinstall, with:

```sh
curl -fsSL https://raw.githubusercontent.com/stacx-lab/kinex/main/install.sh | bash
```

The installer:

- uses your existing Node.js ≥ 22.19 and npm, or asks before installing them;
- checks the downloaded release against its published checksums;
- installs into `~/.local/share/kinex/install` and adds a `kinex` launcher in `~/.local/bin`;
- asks before adding `~/.local/bin` to your `PATH`;
- refuses to overwrite a `kinex` it didn't install, or to hide another `kinex` already on your `PATH`.

`kinex update` only updates installs made by the installer, and never downgrades. After updating, refresh any drivers and tools you copied into a workspace (for example RoboEnv profiles); updates don't rewrite those copies.

### Build from source

```sh
git clone https://github.com/stacx-lab/kinex.git
cd kinex
nvm use
npm ci
npm run build
npm run dev          # run Kinex from source
```

Before submitting changes, run the full check (needs Python 3 on Linux or macOS):

```sh
python3 -m pip install -r packages/core/test/requirements.txt -r packages/setup/test/requirements.txt
npm run check
```

See [AGENTS.md](https://github.com/stacx-lab/kinex/blob/main/AGENTS.md) for contribution guidelines.
