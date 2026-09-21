#!/usr/bin/env node

import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const contentDirectory = new URL('../_posts/', import.meta.url);
const files = (await readdir(contentDirectory)).filter(file => file.endsWith('.md'));

const escapeAttribute = value => value
  .replaceAll('&', '&amp;')
  .replaceAll('"', '&quot;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

for (const file of files) {
  const path = join(contentDirectory.pathname, file);
  const source = await readFile(path, 'utf8');
  if (!/^layout:\s*["']?collection["']?\s*$/m.test(source)) continue;

  const references = new Map();
  for (const match of source.matchAll(/^\[([^\]]+)\]:\s+(\S+)/gm)) {
    references.set(match[1], match[2]);
  }

  let optimized = source.replace(/^!\[([^\]]*)\]\[([^\]]+)\]\s*$/gm, (line, alt, reference) => {
    const url = references.get(reference);
    if (!url) return line;
    return `<p class="gallery-item"><img src="${escapeAttribute(url)}" alt="${escapeAttribute(alt)}" width="1200" height="900" loading="lazy" decoding="async"></p>`;
  });

  let galleryIndex = 0;
  optimized = optimized.replace(
    /<p class="gallery-item"><img ([^>]+)><\/p>/g,
    (line, imageAttributes) => {
      galleryIndex += 1;
      return `<p class="gallery-item"><button type="button" class="gallery-trigger" popovertarget="gallery-lightbox" data-gallery-index="${galleryIndex}"><img ${imageAttributes}></button></p>`;
    },
  );

  if (optimized !== source) await writeFile(path, optimized);
}
