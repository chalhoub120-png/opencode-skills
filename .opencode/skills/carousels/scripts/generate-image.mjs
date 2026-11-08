#!/usr/bin/env node
/* Generate one carousel illustration. Default provider is the free Pollinations
 * service (Flux, no key, no payment). OpenAI (GPT Image 2) remains available
 * via --provider openai when an OPENAI_API_KEY with credits is set.
 *
 * gpt-image-2 only produces opaque images and won't land on an exact brand hex
 * on its own, so after generating, the script snaps the background to an exact
 * color (--bg-hex) — the illustration then sits seamlessly on its slide.
 *
 * Usage:
 *   node generate-image.mjs --prompt "<prompt>"      --out images/slide-04.png
 *   node generate-image.mjs --prompt-file prompt.txt  --out images/slide-04.png
 *
 * Options:
 *   --provider pollinations|openai (default pollinations — free, no key)
 *   --size     1024x1024 (default) | 1024x1536 | 1536x1024
 *   --quality  medium (default) | low | high (OpenAI only)
 *   --bg-hex   #F5F1E8 (default — brand off-white) | any #RRGGBB | none
 *              The generated background is normalized to this exact hex.
 *              Pass `none` to skip normalization.
 *
 * Env:
 *   OPENAI_API_KEY        optional — only needed with --provider openai
 *   CAROUSEL_IMAGE_MODEL  optional, defaults to gpt-image-2 (OpenAI only)
 *
 * Privacy note: Pollinations is an external free service — the prompt text
 * leaves this device when generating. Type-only carousels need no key and
 * no external call at all.
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

/* Load OPENAI_API_KEY from a gitignored .env at the repo root if it isn't
 * already in the environment. */
if (!process.env.OPENAI_API_KEY) {
  try { process.loadEnvFile(arg('env-file', '.env')); } catch { /* no .env — fine */ }
}

const apiKey = process.env.OPENAI_API_KEY;
const provider = arg('provider', 'pollinations');
const useFree = provider === 'pollinations';
if (!apiKey && !useFree) {
  console.error(`
OPENAI_API_KEY is not set (needed only with --provider openai).
Default is the free Pollinations provider — no key, no payment:
  node generate-image.mjs --prompt-file prompt.txt --out images/slide-04.png
Privacy note: Pollinations is external — the prompt text leaves this device.
Type-only carousels need no key and no external call at all.
`);
  process.exit(1);
}

const out = arg('out');
if (!out) { console.error('Missing --out <path>'); process.exit(1); }

let prompt = arg('prompt');
const promptFile = arg('prompt-file');
if (!prompt && promptFile) prompt = (await readFile(promptFile, 'utf8')).trim();
if (!prompt) { console.error('Missing --prompt or --prompt-file'); process.exit(1); }

const model = process.env.CAROUSEL_IMAGE_MODEL || 'gpt-image-2';
const size = arg('size', '1024x1024');
const quality = arg('quality', 'medium');
const bgHex = arg('bg-hex', '#F5F1E8');
const [w, h] = size.split('x').map(Number);

await mkdir(dirname(out), { recursive: true });

async function generateWithPollinations() {
  const url = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=${w}&height=${h}&model=flux&nologo=true&seed=42`;
  console.log(`Generating illustration (free) → ${out}  (pollinations flux, ${size})`);
  const res = await fetch(url);
  if (!res.ok) {
    console.error(`Pollinations error ${res.status}: ${(await res.text()).slice(0, 300)}`);
    process.exit(1);
  }
  await writeFile(out, Buffer.from(await res.arrayBuffer()));
  console.log(`Saved ${out} (free)`);
}

async function generateWithOpenAI() {
  console.log(`Generating illustration → ${out}  (${model}, ${size}, ${quality})`);
  const res = await fetch('https://api.openai.com/v1/images/generations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ model, prompt, size, quality, output_format: 'png', n: 1 }),
  });

  if (!res.ok) {
    const detail = await res.text();
    console.error(`OpenAI API error ${res.status}: ${detail}`);
    let param;
    try { param = JSON.parse(detail)?.error?.param; } catch { /* not json */ }
    if (param === 'model') {
      console.error('\nThe image model was rejected. Set CAROUSEL_IMAGE_MODEL to a ' +
        'model your account has access to (e.g. gpt-image-1).');
    }
    process.exit(1);
  }

  const data = await res.json();
  const b64 = data?.data?.[0]?.b64_json;
  if (!b64) { console.error('No image data in response'); process.exit(1); }
  await writeFile(out, Buffer.from(b64, 'base64'));
  console.log(`Saved ${out}`);
}

if (useFree) {
  await generateWithPollinations();
} else {
  await generateWithOpenAI();
}

if (bgHex.toLowerCase() !== 'none') {
  await normalizeBackground(out, bgHex);
  console.log(`Normalized background to exactly ${bgHex}`);
}

/* Snap the image's background to an exact hex. The illustration is line art —
 * a fairly uniform light background, dark linework, one teal accent — so
 * sampling the corners gives a reliable background reference, and every pixel
 * within `tolerance` of it is recolored to the exact target. Dark lines and the
 * teal accent are far outside the tolerance and untouched. Uses the headless
 * browser's canvas, so no extra dependency. */
async function normalizeBackground(file, hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) { console.error(`Invalid --bg-hex "${hex}" — expected #RRGGBB`); process.exit(1); }
  const target = [
    parseInt(m[1].slice(0, 2), 16),
    parseInt(m[1].slice(2, 4), 16),
    parseInt(m[1].slice(4, 6), 16),
  ];

  let puppeteer;
  try { puppeteer = (await import('puppeteer')).default; }
  catch { console.error('puppeteer is needed for background normalization. Run: npm install puppeteer'); process.exit(1); }

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  const raw = await readFile(file);
  const mime = raw[0] === 0xff && raw[1] === 0xd8 ? 'image/jpeg' : 'image/png';
  const dataUrl = `data:${mime};base64,${raw.toString('base64')}`;

  const outUrl = await page.evaluate(async (src, target, tolerance) => {
    const img = new Image();
    await new Promise((ok, err) => { img.onload = ok; img.onerror = err; img.src = src; });
    const canvas = document.createElement('canvas');
    canvas.width = img.width; canvas.height = img.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const px = data.data;

    // background reference = average of the four 16x16 corners
    const W = canvas.width, H = canvas.height, S = 16;
    let r = 0, g = 0, b = 0, count = 0;
    for (const [ox, oy] of [[0, 0], [W - S, 0], [0, H - S], [W - S, H - S]]) {
      for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
        const i = ((oy + y) * W + (ox + x)) * 4;
        r += px[i]; g += px[i + 1]; b += px[i + 2]; count++;
      }
    }
    const ref = [r / count, g / count, b / count];

    for (let i = 0; i < px.length; i += 4) {
      const d = Math.hypot(px[i] - ref[0], px[i + 1] - ref[1], px[i + 2] - ref[2]);
      if (d <= tolerance) {
        px[i] = target[0]; px[i + 1] = target[1]; px[i + 2] = target[2]; px[i + 3] = 255;
      }
    }
    ctx.putImageData(data, 0, 0);
    return canvas.toDataURL('image/png');
  }, dataUrl, target, 70);

  await browser.close();
  await writeFile(file, Buffer.from(outUrl.split(',')[1], 'base64'));
}
