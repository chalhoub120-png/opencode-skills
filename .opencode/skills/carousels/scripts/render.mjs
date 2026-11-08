#!/usr/bin/env node
/* Render a carousel: screenshot each .slide in slides.html to a PNG, then
 * assemble the PNGs into a print-ready PDF for LinkedIn.
 *
 * Usage:
 *   node render.mjs --slides <run>/slides.html --out <run>/publish
 *
 * Produces:
 *   <out>/slide-01.png ... slide-NN.png   (1080x1350, Instagram)
 *   <out>/carousel.pdf                    (one slide per page, LinkedIn)
 */

import { mkdir, writeFile, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const slidesPath = arg('slides');
const outDir = arg('out');
if (!slidesPath || !outDir) {
  console.error('Usage: node render.mjs --slides <slides.html> --out <publish-dir>');
  process.exit(1);
}
if (!existsSync(slidesPath)) {
  console.error(`slides.html not found: ${slidesPath}`);
  process.exit(1);
}

const W = 1080;
const H = 1350;

let puppeteer;
try {
  puppeteer = (await import('puppeteer')).default;
} catch {
  console.error('puppeteer is not installed. From the repo root run:\n  npm install puppeteer');
  process.exit(1);
}

let browser;
try {
  browser = await puppeteer.launch({ headless: true });
} catch (err) {
  console.error('Could not launch the headless browser. Install it with:\n' +
    '  npx puppeteer browsers install chrome\n\n' + err.message);
  process.exit(1);
}

await mkdir(outDir, { recursive: true });

const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve(slidesPath)).href, { waitUntil: 'networkidle0' });
await page.evaluate(() => document.fonts.ready);

const slides = await page.$$('.slide');
if (slides.length === 0) {
  console.error('No .slide elements found in slides.html');
  await browser.close();
  process.exit(1);
}
console.log(`Found ${slides.length} slides`);

const pngPaths = [];
for (let i = 0; i < slides.length; i++) {
  const n = String(i + 1).padStart(2, '0');
  const file = join(outDir, `slide-${n}.png`);
  await slides[i].screenshot({ path: file });
  pngPaths.push(resolve(file));
  console.log(`  rendered slide-${n}.png`);
}

/* Assemble the PDF — one PNG per page, full bleed, no margins.
 * Written to a real file in outDir so the PNGs load as same-scheme file://
 * resources (a setContent page has a null origin and is blocked from file://). */
const pdfHtml = `<!DOCTYPE html><html><head><style>
  @page { size: ${W}px ${H}px; margin: 0; }
  html, body { margin: 0; padding: 0; }
  .page { width: ${W}px; height: ${H}px; page-break-after: always; }
  .page:last-child { page-break-after: auto; }
  img { width: ${W}px; height: ${H}px; display: block; }
</style></head><body>${
  pngPaths.map((p) => `<div class="page"><img src="${pathToFileURL(p).href}"></div>`).join('')
}</body></html>`;

const pdfSrcPath = join(outDir, '.pdf-source.html');
await writeFile(pdfSrcPath, pdfHtml);
const pdfPage = await browser.newPage();
await pdfPage.goto(pathToFileURL(resolve(pdfSrcPath)).href, { waitUntil: 'networkidle0' });
const pdfPath = join(outDir, 'carousel.pdf');
await pdfPage.pdf({
  path: pdfPath,
  width: `${W}px`,
  height: `${H}px`,
  printBackground: true,
  pageRanges: `1-${pngPaths.length}`,
});
await rm(pdfSrcPath, { force: true });
console.log(`Assembled ${pdfPath}`);

await browser.close();
console.log(`\nDone. ${pngPaths.length} PNGs + carousel.pdf in ${outDir}`);
