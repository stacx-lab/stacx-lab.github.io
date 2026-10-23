import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { docGroups } from './config';

const docs = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/docs' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    group: z.enum(docGroups),
    order: z.number().int(),
    label: z.string().optional(),
    sources: z.array(z.string()).default([]),
  }),
});

export const collections = { docs };
