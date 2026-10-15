// Snapshot of the dataset revision used by the public benchmark Space.
// Aggregate valid episodes by case: successes / episodes; sum costLow / costHigh and tokens.
// Total tokens include fresh input, cache reads, and output.
// Each Astra setting has one episode for each of the same 132 tasks.
export const benchmark = {
  source: 'https://huggingface.co/spaces/stacx-lab/kinex-benchmark-release',
  data: 'https://huggingface.co/datasets/stacx-lab/kinex-benchmark-release/resolve/fc05262786d2ee6abcef953c8b7cf974a2e088e1/data.json',
  tasks: 132,
  settings: [
    { id: 'control', label: 'Codex + Bare action API', successes: 96, cost: 436.35038, tokens: 280141566 },
    { id: 'device', label: 'Codex + Device API', successes: 96, cost: 285.303312, tokens: 169881784 },
    { id: 'kinex', label: 'Kinex', successes: 103, cost: 249.27031, tokens: 137518999 },
  ],
};

// Per-benchmark aggregates from the same pinned dataset revision above.
const environments = [
  { id: 'libero', label: 'LIBERO', tasks: 40, results: [
    { successes: 34, cost: 44.570138 },
    { successes: 34, cost: 56.374848 },
    { successes: 34, cost: 51.157162 },
  ] },
  { id: 'robotwin', label: 'RoboTwin', tasks: 50, results: [
    { successes: 41, cost: 165.944076 },
    { successes: 43, cost: 69.423736 },
    { successes: 45, cost: 71.205016 },
  ] },
  { id: 'robodojo', label: 'RoboDojo', tasks: 42, results: [
    { successes: 21, cost: 225.836166 },
    { successes: 19, cost: 159.504728 },
    { successes: 24, cost: 126.908132 },
  ] },
];

// Average weights each task equally, rather than each benchmark equally.
export const benchmarkScopes = [
  { id: 'average', label: 'Average', tasks: benchmark.tasks, settings: benchmark.settings },
  ...environments.map(({ results, ...environment }) => ({
    ...environment,
    settings: results.map((result, index) => ({
      id: benchmark.settings[index].id,
      label: benchmark.settings[index].label,
      ...result,
    })),
  })),
];

const [baseline, , kinex] = benchmark.settings;
export const astraComparison = {
  baselineSuccessRate: baseline.successes / benchmark.tasks * 100,
  kinexSuccessRate: kinex.successes / benchmark.tasks * 100,
  successGainPoints: (kinex.successes - baseline.successes) / benchmark.tasks * 100,
  tokenReductionPercent: (1 - kinex.tokens / baseline.tokens) * 100,
  costReductionPercent: (1 - kinex.cost / baseline.cost) * 100,
};
