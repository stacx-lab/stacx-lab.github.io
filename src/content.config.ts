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

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    published: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/),
    author: z.object({ name: z.string(), url: z.string().url().optional() }).optional(),
    readingTime: z.string().optional(),
    topic: z.string().optional(),
    contents: z.array(z.object({ id: z.string(), label: z.string(), number: z.string() })).default([]),
  }),
});

export const collections = { docs, blog };
