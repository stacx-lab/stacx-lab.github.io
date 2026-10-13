---
title: Slash commands
description: The commands you'll use inside a Kinex session, plus keyboard shortcuts.
group: Reference
order: 20
sources: ["docs/commands.md", "packages/core/src/commands.ts", "packages/setup/src/integration.ts", "src/integration/extension.ts"]
---

Type `/` in a session to search every available command. Device names complete with Tab. Device and recording commands run immediately, without involving the model; they also work from the shell, such as `kinex run "/ping arm"`.

## Devices

| Command | Does |
| --- | --- |
| `/devices` | List devices and whether each is set to load |
| `/load <device\|all>` | Connect a device and wait until it's ready |
| `/unload <device\|all>` | Disconnect a device and release its resources |
| `/ping <device\|all>` | Check a device's live status, without starting anything |
| `/stop [device]` | Stop the agent and the robot's motion, without asking for approval |
| `/register <type>` | Ask the agent to set up a new device of this type or template |
| `/unregister <device>` | After confirmation, remove a device's profile, driver and files (needs the TUI; from the shell it's cancelled) |

To restart a device, run `/unload` and then `/load`.

## Recording

| Command | Does |
| --- | --- |
| `/record start <device=Hz ...> [instruction]` | Start recording these devices at these rates |
| `/record snap <device ...> [note]` | Save one snapshot and mark the moment |
| `/record status` | Show the current and recent recordings |
| `/record stop [success\|failure\|partial] [note]` | Stop and save, with an optional outcome |

Add `--verbose` right after the action (for example `/record status --verbose`) to include empty fields. See [Recording](/docs/recording/).

## Setup

These hand a guided task to the agent, so they need a model.

| Command | Does |
| --- | --- |
| `/onboarding [description]` | Set up the robot for a task: devices, checks and any calibration it needs |
| `/calibrate [what]` | Calibrate what you describe, or continue the current task's calibration |

See [Onboarding & calibration](/docs/onboarding/).

## Approvals

| Command | Does |
| --- | --- |
| `/mode [ask\|auto\|yolo]` | Choose how much the agent asks for approval; bare `/mode` opens a picker |

See [Approval modes](/docs/agent/#approval-modes).

## Agent and sessions

These come from Pi, the coding agent Kinex is built on. See [Working with the agent](/docs/agent/).

| Command | Does |
| --- | --- |
| `/login`, `/logout` | Connect or disconnect a model provider |
| `/model` | Choose the model |
| `/thinking` | Set reasoning effort |
| `/new`, `/resume` | Start a new session, or switch to a saved one |
| `/tree`, `/fork`, `/clone` | Browse branches, branch from an earlier message, or copy the session |
| `/name`, `/session` | Name the session, or show its details |
| `/compact [instructions]` | Summarize the conversation to free up context |
| `/export [path]` | Save the session as HTML or JSONL |
| `/copy` | Copy the agent's last reply |
| `/settings`, `/hotkeys` | Open preferences, or list keyboard shortcuts |
| `/reload` | Reload extensions, skills, prompts and themes (not devices) |
| `/quit` | Exit Kinex |

Installed extensions and prompt templates can add their own commands. Start a line with `!` to run it as a shell command.

## Keyboard shortcuts

| Key | Does |
| --- | --- |
| Enter | Send; while the agent is working, steer it |
| Shift+Enter | New line |
| Alt+Enter | Queue a follow-up for when the agent finishes |
| Escape | Interrupt the agent (use `/stop` to stop the robot too) |
| Ctrl+O | Expand or collapse tool calls and their output |
