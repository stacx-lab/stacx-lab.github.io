type GalleryVideo = {
  id: string;
  title: string;
  description: string;
  highlights?: { title: string; text: string }[];
  duration: string;
  robot: string;
  model: string;
  effort: string;
  environment: string;
};

export const galleryVideos: GalleryVideo[] = [
  {
    id: 'abc-yam-cube',
    title: 'Solving a 2x2 cube',
    description: 'Active sensing, solution reasoning, and precision control with collision avoidance.',
    highlights: [
      { title: 'Active sensing', text: 'Moves wrist cameras to inspect all six faces of the cube.' },
      { title: 'Solution reasoning', text: 'Reconstructs the cube state and works out a solving sequence.' },
      { title: 'Precision & collision avoidance', text: 'Coordinates layer turns and handoffs while avoiding collisions between arms, grippers, and cameras.' },
    ],
    duration: '01:15',
    robot: 'YAM',
    model: 'GPT-6-Astra',
    effort: 'medium',
    environment: 'Real world',
  },
  {
    id: 'go2-trash-clean',
    title: 'Collecting litter',
    description: 'Coordinates locomotion and manipulation, then adapts its grasp after a human moves the litter.',
    highlights: [
      { title: 'Locomotion & manipulation', text: 'Coordinates the Go2 base and D1 arm to approach, grasp, carry, and deposit litter in the bin.' },
      { title: 'Robustness & adaptiveness', text: 'After a person sweeps the litter away, detects the missed grasp, observes the changed scene, and repositions to grasp it again.' },
    ],
    duration: '01:29',
    robot: 'Go2 + D1',
    model: 'GPT-6-Astra',
    effort: 'medium',
    environment: 'Real world',
  },
  {
    id: 'real-hang-mug',
    title: 'Hang a red cup',
    description: 'Recovers from a failed hang and actively moves the right-arm camera to verify the cup is supported by the peg.',
    highlights: [
      { title: 'Error recovery', text: 'After the first attempt fails, recovers the cup, replans the insertion, and completes the hang.' },
      { title: 'Active sensing', text: 'During recovery, repositions the right arm for a clearer camera view to check whether the cup is actually hanging on the peg.' },
    ],
    duration: '01:00',
    robot: 'YAM',
    model: 'GPT-6-Astra',
    effort: 'high',
    environment: 'Real world',
  },
  {
    id: 'yam-hang-mug',
    title: 'Hang a mug on the rack',
    description: 'Follow the agent as it measures the scene, grasps the mug, and verifies the release onto the rack in simulation.',
    duration: '00:45',
    robot: 'YAM',
    model: 'GPT-6-Astra',
    effort: 'high',
    environment: 'Simulator',
  },
];
