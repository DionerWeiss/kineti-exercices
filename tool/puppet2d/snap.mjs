// node snap.mjs <anim.json> <out prefix> <frames: 0,10,20 | all/N> [size=1080]
// Renders single frames of a Lottie (lottie-web canvas, headless Chromium) to <prefix>_<frame>.png, for close checks.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [src, prefix, framesArg, sizeArg] = process.argv.slice(2);
const size = Number(sizeArg || 1080);
const anim = JSON.parse(fs.readFileSync(src, 'utf8'));
const exe = `${process.env.HOME}/.cache/ms-playwright/${fs.readdirSync(process.env.HOME + "/.cache/ms-playwright").find(d => d.startsWith("chromium_headless_shell"))}/chrome-headless-shell-linux64/chrome-headless-shell`;
const browser = await chromium.launch({ executablePath: exe });
const W = size, H = Math.round(size * anim.h / anim.w);
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('pageerror', e => console.error('PAGEERROR', e.message));
await page.setContent(`<html><body style="margin:0;background:#fff"><div id="c" style="width:${W}px;height:${H}px"></div></body></html>`);
await page.addScriptTag({ path: path.join(HERE, 'node_modules/lottie-web/build/player/lottie.min.js') });
const n = await page.evaluate((data) => {
  window.A = lottie.loadAnimation({ container: document.getElementById('c'), renderer: 'canvas', loop: false, autoplay: false, animationData: data,
    rendererSettings: { clearCanvas: true, dpr: 1 } });
  return window.A.totalFrames;
}, anim);
let frames;
if (framesArg.startsWith('all/')) {
  const k = Number(framesArg.split('/')[1]);
  frames = Array.from({ length: k }, (_, i) => Math.floor(i * n / k));
} else frames = framesArg.split(',').map(Number);
for (const f of frames) {
  const b64 = await page.evaluate((f) => { A.goToAndStop(f, true); return document.querySelector('canvas').toDataURL('image/png').split(',')[1]; }, f);
  fs.writeFileSync(`${prefix}_${String(f).padStart(3, '0')}.png`, Buffer.from(b64, 'base64'));
}
await browser.close();
console.log(n, 'frames; wrote', frames.length);
