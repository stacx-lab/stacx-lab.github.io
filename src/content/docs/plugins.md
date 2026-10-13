---
title: Plugin systems
description: Install and manage Pi plugins in Kinex, and use Kinex itself as a plugin in Pi, OpenCode or Codex.
group: Guides
order: 70
label: Plugin systems
sources: ["README.md", "src/packages.ts", "src/integration/default-extensions.ts", "packages/setup/README.md", "docs/agent-integration.md", "docs/overview.md"]
---

Plugins work in two directions with Kinex:

- **Into Kinex.** Kinex is built on [Pi](https://pi.dev), so it can install and run plugins from Pi's ecosystem: extensions, skills, prompt templates and themes.
- **Out of Kinex.** Kinex's robotics layer is itself packaged as plugins, so you can use your devices, tools and skills from Pi, OpenCode or Codex instead of the Kinex app.

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

Packages install for your user by default; add `-l` to install for the current project only. **Restart Kinex** after installing, updating or removing a package so the change takes effect. See Pi's [package documentation](https://github.com/earendil-works/pi/blob/v1.1.0/packages/coding-agent/docs/packages.md) to write your own.

## Using Kinex from other harnesses

If you'd rather keep working in your usual coding agent, the [kinex-plugins](https://github.com/stacx-lab/kinex-plugins) repository brings Kinex's robotics layer to it: your devices, robotics tools, skills and workspace context. Your harness keeps its own coding tools, sessions, credentials and approval UI. You don't need the Kinex app installed. Each plugin works with the same `.kinex/` workspace, so you can switch between Kinex and your harness on the same robot.

| Harness | How Kinex plugs in |
| --- | --- |
| **Pi** | A native Pi extension. Kinex's slash commands and tools appear directly in Pi. |
| **OpenCode** | An OpenCode plugin, with a server part for the model's tools and a TUI part for slash commands. |
| **Codex** | A local MCP server that Codex connects to, plus a small CLI for direct commands. |

All three share the same robotics core, so devices, tools, skills, onboarding and calibration behave just as they do in Kinex. Plugin releases are versioned separately from Kinex.

### Installing a plugin

The plugins aren't on npm yet, so you build them from the repository and install the packed release. They need Node.js 22.22.2 or newer (see the repository's `.nvmrc`):

```sh
git clone https://github.com/stacx-lab/kinex-plugins.git
cd kinex-plugins
npm ci && npm run build
npm run pack -- /tmp/kinex-plugins-release
```

Then install the core packages together with the plugin for your harness, and register it. For Pi:

```sh
npm install --prefix ~/kinex-plugins \
  /tmp/kinex-plugins-release/kinex-core-*.tgz \
  /tmp/kinex-plugins-release/kinex-setup-*.tgz \
  /tmp/kinex-plugins-release/kinex-pi-*.tgz
pi install ~/kinex-plugins/node_modules/@kinex/pi
```

For OpenCode, install `kinex-opencode-*.tgz` the same way and register it with `opencode plugin file://…/@kinex/opencode`. For Codex, install `kinex-codex-*.tgz` and add Kinex as an MCP server in `.codex/config.toml`, pointing it at your robot workspace. Each plugin's README in the repository has the exact steps.

### Using it

Open your robot workspace in your harness.

- **In Pi and OpenCode**, Kinex's commands work as usual: `/devices`, `/load`, `/ping`, `/stop`, `/record`, `/onboarding`, `/calibrate` and so on. Each also has a `/kinex-` alias, such as `/kinex-devices`, in case the harness already uses the same name.
- **In Pi**, the agent gets Kinex's tools and skills alongside its own.
- **In OpenCode and Codex**, the agent reaches Kinex through two tools: `kinex_tools` lists what's available and loads skills, and `kinex_call` runs a tool. Codex also gets `kinex_stop`, which stops the robot without Kinex's approval check (set `approval_mode = "auto"` for it in Codex's config, as the plugin README shows, so Codex doesn't ask either). Check the Codex connection with `/mcp`.

## Building your own integration

To bring Kinex to a host that isn't covered, build on `@kinex/core` directly. It has no agent, UI or model dependency: you create a runtime for a workspace, register its tools with your host, and supply a callback that asks the user for permission.

```ts
import { createKinexRuntime } from "@kinex/core"
import { coreContribution, composeContributions } from "@kinex/core/integration"

const runtime = createKinexRuntime({ directory: process.cwd(), host: { ask: async request => { /* allow, or throw to deny */ } } })
const capabilities = composeContributions([coreContribution(runtime)])
```

Add `@kinex/setup` for onboarding and calibration. The [core README](https://github.com/stacx-lab/kinex/blob/main/packages/core/README.md) and [setup README](https://github.com/stacx-lab/kinex/blob/main/packages/setup/README.md) cover the API.
