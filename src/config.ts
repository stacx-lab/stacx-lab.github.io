// Single edit point for site-wide facts. Bump `version` on each release.
export const site = {
  name: 'kinex',
  version: '1.0.0',
  tagline: 'A robotics harness for coding agents.',
  description:
    'Kinex is a ROS 2-compatible robotics harness for coding agents. Connect ROS 2 robots, simulators and real hardware through devices, tools and skills. Supports ROS 2 Jazzy on Ubuntu 24.04.',
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
