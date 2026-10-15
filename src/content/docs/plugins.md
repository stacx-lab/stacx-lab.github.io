---
title: Plugin systems
description: Install and manage Pi plugins in Kinex, and use Kinex itself as a plugin in Pi, Claude Code or Codex.
group: Guides
order: 70
label: Plugin systems
sources: ["README.md", "src/packages.ts", "src/integration/default-extensions.ts", "packages/setup/README.md", "docs/agent-integration.md", "docs/overview.md"]
---

Plugins work in two directions with Kinex:

- **Into Kinex.** Kinex is built on [Pi](https://pi.dev), so it can install and run plugins from Pi's ecosystem: extensions, skills, prompt templates and themes.
- **Out of Kinex.** Kinex's robotics layer is itself packaged as plugins, so you can use your devices, tools and skills from Pi, Claude Code or Codex instead of the Kinex app.

## Installing Pi plugins

Pi plugins are distributed as packages, from npm, a Git repository or a local folder. Kinex manages them with the same commands as Pi. Browse what's available at [pi.dev/packages](https://pi.dev/packages).

Kinex already bundles two: [pi-web-search](https://www.npmjs.com/package/pi-web-search) for web search and [pi-btw](https://www.npmjs.com/package/pi-btw) for side conversations.

For example, to pin web search to a specific version, check it, and later go back to the bundled one:

```sh
kinex install npm:pi-web-search@1.7.0      # install a specific version, replacing the bundled copy
kinex list                                 # see installed and bundled packages
kinex update --extensions                  # update installed packages, keeping version pins
kinex remove npm:pi-web-search             # remove it; the bundled version takes over again
```

Other sources work the same way:

```sh
kinex install git:github.com/me/my-pi-package@v1    # from a Git repository, at a tag
kinex install ./my-pi-package -l                    # from a local folder, for this project only
kinex update npm:pi-web-search                      # update a single package
```

Packages install for your user by default; add `-l` to install for the current project only. **Restart Kinex** after installing, updating or removing a package so the change takes effect. See Pi's [package documentation](https://github.com/earendil-works/pi/blob/v1.2.0/packages/coding-agent/docs/packages.md) to write your own.

## Using Kinex from other harnesses

The [kinex-plugins](https://github.com/stacx-lab/kinex-plugins) repository currently supports **Pi, Claude Code and Codex**. It brings Kinex's devices, robotics tools, skills and workspace context into those hosts. Your harness keeps its own coding tools, sessions, credentials and approval UI. You don't need the standalone Kinex app installed. OpenCode is not currently supported.

| Harness | How Kinex plugs in |
| --- | --- |
| **Pi** | A Pi extension with direct lifecycle commands and approval/questionnaire dialogs, connected to the shared MCP server. |
| **Claude Code** | A marketplace plugin with shared Kinex skills and MCP server configuration. |
| **Codex** | A marketplace plugin with shared Kinex skills and MCP server configuration. |

All three use the shared `@kinex/mcp` adapter and packed `@kinex/core`/`@kinex/setup` snapshots. Plugin releases are versioned separately; updating standalone Kinex does not update a plugin's snapshot. Check the plugin's bundled version before relying on newly added tools or runtime behavior. Hosts can use the same `.kinex/` workspace in separate sessions; independent hosts do not coordinate concurrent control of the same physical devices.

### Installing a plugin

Install from a local checkout on Linux or macOS; npm publication is not required. The plugins need Node.js 22.22.2 or newer. Build with the repository's selected Node version:

```sh
git clone https://github.com/stacx-lab/kinex-plugins.git
cd kinex-plugins
nvm use
npm ci
npm run build
export KINEX_SOURCE="$PWD"
```

For Pi, install the package directly from this checkout:

```sh
pi install "$KINEX_SOURCE/packages/pi"
```

For Claude Code and Codex, follow the [local marketplace setup](https://github.com/stacx-lab/kinex-plugins#claude-code-and-codex). It copies the generated bundles outside the checkout and points their MCP configurations at the built local server with host-managed approvals. Install `kinex@kinex-plugins` through the selected host. Keep the checkout and its dependencies in place; the installed plugins use its built files. Packed tarball installation is also covered in the [shared server README](https://github.com/stacx-lab/kinex-plugins/blob/main/packages/mcp/README.md#local-tarballs-before-publication).

### Using it

Open your robot workspace and launch a new host session:

```sh
cd /path/to/robot-workspace
export KINEX_WORKSPACE="$PWD"
# Launch pi, claude, or codex.
```

Connecting the plugin leaves robotics inactive. Use these lifecycle commands or skills:

| Action | Pi direct command | Claude Code or Codex request |
| --- | --- | --- |
| Start the runtime and restore configured loaded devices | `/kinex-start` | “Start Kinex” |
| Inspect state, permission mode and recordings without activating robotics | `/kinex-status` | “Show Kinex status” |
| Cancel work, finalize recordings and release devices while keeping the host open | `/kinex-end` | “End Kinex” |

Claude Code and Codex include the corresponding `kinex-start`, `kinex-status` and `kinex-end` skills. In Codex, explicitly ask “Start Kinex”; installing or enabling the plugin does not activate robotics. Starting after an end creates a fresh runtime. Normal host exit also disposes its runtime; borrowed external services remain running.

All three hosts discover current tools, skills, workflows and context through `kinex_tools`, and execute robotics tools through `kinex_call`. The shared server also exposes `kinex_start`, `kinex_status`, `kinex_shutdown` and `kinex_stop`. Pi's direct lifecycle commands run without a model round trip.

The plugins use **host-managed approvals** by default. Explicit `allow`, `ask` and `deny` rules in `kinex.json` still apply; setup questionnaires still require answers. See the [plugin permissions documentation](https://github.com/stacx-lab/kinex-plugins#permissions) for details and how to restore Kinex-managed approvals.

## Building your own integration

To bring Kinex to a host that isn't covered, build on `@kinex/core` directly. It has no agent, UI or model dependency: you create a runtime for a workspace, register its tools with your host, and supply a callback that asks the user for permission.

```ts
import { createKinexRuntime } from "@kinex/core"
import { coreContribution, composeContributions } from "@kinex/core/integration"

const runtime = createKinexRuntime({ directory: process.cwd(), host: { ask: async request => { /* allow, or throw to deny */ } } })
const capabilities = composeContributions([coreContribution(runtime)])
```

Add `@kinex/setup` for onboarding and calibration. The [core README](https://github.com/stacx-lab/kinex/blob/main/packages/core/README.md) and [setup README](https://github.com/stacx-lab/kinex/blob/main/packages/setup/README.md) cover the API.
