import { getCollection, type CollectionEntry } from 'astro:content';
import { docGroups } from '../config';
import { kinexUrl } from './url';

export type Doc = CollectionEntry<'docs'>;

/** Docs in sidebar order: group (as listed in config), then `order`. */
export async function getDocs(): Promise<Doc[]> {
  const docs = await getCollection('docs');
  const g = (d: Doc) => docGroups.indexOf(d.data.group);
  return docs.sort((a, b) => g(a) - g(b) || a.data.order - b.data.order || a.id.localeCompare(b.id));
}

export const docSlug = (d: Doc) => (d.id === 'index' ? undefined : d.id);
export const docHref = (d: Doc) => kinexUrl(d.id === 'index' ? '/docs/' : `/docs/${d.id}/`);
