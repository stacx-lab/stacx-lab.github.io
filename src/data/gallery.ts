export type GalleryHighlight = {
  title: string;
  text: string;
  moments?: { start: number; end: number }[];
};

type GalleryVideo = {
  id: string;
  title: string;
  description: string;
  highlights?: GalleryHighlight[];
  duration: string;
  robot: string;
  embodiment: string;
  model: string;
  effort: string;
  environment: string;
};

// Highlight times are seconds in the delivered video, from gallery/<id>/<id>.provenance.json.
// Cube: entries 108–170, 170–178, 378–440. Go2: the source 306–311 broom
// disturbance through entry 278 is robustness; entries 366–402 show the return
// for remaining litter (spatial memory); the rest is locomotion/manipulation.
// Red cup: entries 260–326, 413–428.
export const galleryVideos: GalleryVideo[] = [
  {
    id: 'abc-yam-cube',
    title: 'Solving a 2x2 cube',
    description: 'Active sensing, solution reasoning, and precision control with collision avoidance.',
    highlights: [
      { moments: [{ start: 5.90, end: 12.21 }], title: 'Active sensing', text: 'Moves wrist cameras to inspect all six faces of the cube.' },
      { moments: [{ start: 12.21, end: 13.99 }], title: 'Solution reasoning', text: 'Reconstructs the cube state and works out a solving sequence.' },
      { moments: [{ start: 56.22, end: 68.06 }], title: 'Precision & collision avoidance', text: 'Coordinates layer turns and handoffs while avoiding collisions between arms, grippers, and cameras.' },
    ],
    duration: '01:15',
    robot: 'YAM',
    embodiment: 'Dual arm',
    model: 'GPT-6-Astra',
    effort: 'medium',
    environment: 'Real world',
  },
  {
    id: 'teleavatar-tube-transfer',
    title: 'Transferring a test tube',
    description: 'Coordinates the mobile base, lift, and arms to transfer a tube between racks, using wrist-camera views to recover from guide-rim contact.',
    highlights: [
      { moments: [{ start: 22.39, end: 31.99 }], title: 'Mobile manipulation', text: 'Turns to locate the destination rack, then coordinates the omniwheel base, lift, and arm to reach it. Visible tether assistance is labeled in the video.' },
      { moments: [{ start: 31.99, end: 35.14 }, { start: 61.67, end: 64.44 }], title: 'Active sensing', text: 'Repositions the left wrist camera to inspect tube clearance and both rack guides while the right arm carries and inserts the tube.' },
      { moments: [{ start: 42.50, end: 53.96 }], title: 'Precision & recovery', text: 'Stops at suspected guide-rim contact, retracts, and corrects alignment before retrying the insertion in small, slow steps.' },
    ],
    duration: '01:15',
    robot: 'TeleAvatar',
    embodiment: 'Wheeled dual-arm mobile manipulator',
    model: 'GPT-6-Astra',
    effort: 'high',
    environment: 'Real world',
  },
  {
    id: 'go2-trash-clean',
    title: 'Collecting litter',
    description: 'Coordinates locomotion and manipulation, adapts its grasp after a human moves the litter, and returns to previously observed litter locations.',
    highlights: [
      { moments: [{ start: 12.81, end: 38.03 }], title: 'Robustness & adaptiveness', text: 'After a person sweeps the litter away, detects the missed grasp, observes the changed scene, and repositions to grasp it again.' },
      { moments: [{ start: 0, end: 12.81 }, { start: 38.03, end: 50.24 }, { start: 59.48, end: 89 }], title: 'Locomotion & manipulation', text: 'Coordinates the Go2 base and D1 arm to approach, grasp, carry, and deposit litter in the bin.' },
      { moments: [{ start: 50.24, end: 59.48 }], title: 'Spatial memory', text: 'After the first deposit, returns to the previously observed litter area and locates the next piece to collect.' },
    ],
    duration: '01:29',
    robot: 'Go2 + D1',
    embodiment: 'Legged mobile manipulator',
    model: 'GPT-6-Astra',
    effort: 'medium',
    environment: 'Real world',
  },
  {
    id: 'real-hang-mug',
    title: 'Hanging a red cup',
    description: 'Recovers from a failed hang and actively moves the right-arm camera to verify the cup is supported by the peg.',
    highlights: [
      { moments: [{ start: 20.47, end: 31.73 }], title: 'Error recovery', text: 'After the first attempt fails, recovers the cup, replans the insertion, and completes the hang.' },
      { moments: [{ start: 40.16, end: 47.91 }], title: 'Active sensing', text: 'During recovery, repositions the right arm for a clearer camera view to check whether the cup is actually hanging on the peg.' },
    ],
    duration: '01:00',
    robot: 'YAM',
    embodiment: 'Dual arm',
    model: 'GPT-6-Astra',
    effort: 'high',
    environment: 'Real world',
  },
  {
    id: 'xarm-sort',
    title: 'Sorting objects by color',
    description: 'Applies an open vocabulary color rule to varied objects and replans grasps after misses and slips.',
    highlights: [
      { title: 'Open vocabulary generalization', text: 'Sorts toy figures, a cube, corn, and a pineapple from a natural-language rule: anything containing blue goes left; everything else goes right.' },
      { title: 'Error recovery + grasp planning', text: 'Uses wrist-camera depth to rotate the grasp after missing the corn, then relocates a slipped cube and grasps it more deeply before retrying.' },
    ],
    duration: '01:00',
    robot: 'xArm 7',
    embodiment: 'Single arm',
    model: 'GPT-6-Astra',
    effort: 'medium',
    environment: 'Real world',
  },
];
