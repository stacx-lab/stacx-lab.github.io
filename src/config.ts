// Single edit point for site-wide facts. Bump `version` on each release.
export const site = {
  name: 'kinex',
  version: '1.0.0',
  tagline: 'A robotics harness for coding agents.',
  description:
    'Kinex is a robotics harness for coding agents, built on the Pi coding agent. Devices, tools and skills give agents access to robots, simulators and models.',
  repo: 'https://github.com/stacx-lab/kinex',
  editBase: 'https://github.com/stacx-lab/stacx-lab.github.io/edit/main/src/content/',
  install: 'curl -fsSL https://raw.githubusercontent.com/stacx-lab/kinex/main/install.sh | bash',
};

export const nav = [
  { label: 'Docs', href: '/docs/' },
  { label: 'Blog', href: '/blog/' },
];

// Sidebar group order. Every doc's `group` frontmatter must be one of these.
export const docGroups = ['Get started', 'Concepts', 'Guides', 'Reference'] as const;
