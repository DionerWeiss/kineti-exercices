// node render.mjs <anim.json> <out.mp4> [size=540] [fpsMult=1] [minSeconds=0]
// Renders a Lottie with lottie-web (canvas) in headless Chromium. fpsMult 2 renders in-between frames (lottie
// interpolates the keys), so a 30 fps animation becomes a smooth 60 fps video. minSeconds repeats the cycle
// (at least twice when set) so a short move can be followed.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [src, out, sizeArg, multArg, minArg] = process.argv.slice(2);
const size = Number(sizeArg || 540);
const mult = Number(multArg || 1);
const minSec = Number(minArg || 0);
const anim = JSON.parse(fs.readFileSync(src, 'utf8'));
const exe = `${process.env.HOME}/.cache/ms-playwright/${fs.readdirSync(process.env.HOME + "/.cache/ms-playwright").find(d => d.startsWith("chromium_headless_shell"))}/chrome-headless-shell-linux64/chrome-headless-shell`;
const browser = await chromium.launch({ executablePath: exe });
const W = size, H = Math.round(size * anim.h / anim.w);
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('pageerror', e => console.error('PAGEERROR', e.message));
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('CONSOLE', m.text()); });
await page.setContent(`<html><body style="margin:0;background:#fff"><div id="c" style="width:${W}px;height:${H}px"></div></body></html>`);
await page.addScriptTag({ path: path.join(HERE, 'node_modules/lottie-web/build/player/lottie.min.js') });
const n = await page.evaluate((data) => {
  window.A = lottie.loadAnimation({ container: document.getElementById('c'), renderer: 'canvas', loop: false, autoplay: false, animationData: data,
    rendererSettings: { clearCanvas: true, dpr: 1 } });
  return window.A.totalFrames;
}, anim);
// frames go to local temp (TMPDIR), not next to the output: a Windows drive under WSL makes thousands of PNG writes slow
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lottie-frames-'));
const steps = Math.round(n * mult);
for (let k = 0; k < steps; k++) {
  const f = k / mult;
  const b64 = await page.evaluate((f) => { A.goToAndStop(f, true); return document.querySelector('canvas').toDataURL('image/png').split(',')[1]; }, f);
  fs.writeFileSync(path.join(tmp, `f_${String(k).padStart(5, '0')}.png`), Buffer.from(b64, 'base64'));
}
await browser.close();
const fps = anim.fr * mult;
const cycle = path.join(tmp, 'cycle.mp4');
execFileSync('ffmpeg', ['-nostdin', '-v', 'error', '-y', '-framerate', String(fps), '-i', path.join(tmp, 'f_%05d.png'),
  '-vf', 'format=yuv420p,pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
  '-tune', 'animation', '-g', String(fps * 2), cycle]);
const dur = n / anim.fr;
const loops = minSec > 0 ? Math.max(2, Math.ceil(minSec / dur)) : 1;
execFileSync('ffmpeg', ['-nostdin', '-v', 'error', '-y', '-stream_loop', String(loops - 1), '-i', cycle, '-c', 'copy',
  '-movflags', '+faststart', out]);
fs.rmSync(tmp, { recursive: true });
console.log(out, n, 'frames', `${fps}fps`, `${loops}x`, `${(loops * dur).toFixed(1)}s`);
