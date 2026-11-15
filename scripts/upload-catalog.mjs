// node --env-file=.env.local scripts/upload-catalog.mjs [--dry-run]
import { readFile, stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { S3Client, HeadObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3';

const root = process.env.CATALOG_VIDEO_ROOT || '/mnt/e/mannequin';
const sources = [['manequim', 'videos', i => i.man], ['lottie', 'puppet2d/final', i => i.lottie.video], ['render3d', 'avatar_man/out/videos_final', i => i.r3d !== 'sem vídeo']];
const raw = await readFile('public/catalogo/data.js', 'utf8');
const catalog = JSON.parse(raw.replace(/^window\.CATALOG=/, '').replace(/;\s*$/, ''));
const jobs = [];
for (const item of catalog.items) for (const [kind, dir, available] of sources) if (available(item)) {
  if (!/^[\w-]+$/.test(item.id)) throw new Error(`ID inválido: ${item.id}`);
  const path = `${root}/${dir}/${item.id}.mp4`;
  const info = await stat(path);
  jobs.push({ path, key: `catalogo/${kind}/${item.id}.mp4`, size: info.size });
}
if (process.env.CATALOG_RETRY_FILE) {
  const keys = new Set((await readFile(process.env.CATALOG_RETRY_FILE, 'utf8')).split('\n').filter(Boolean));
  for (let i = jobs.length - 1; i >= 0; i--) if (!keys.has(jobs[i].key)) jobs.splice(i, 1);
}
console.log(`${jobs.length} vídeos, ${(jobs.reduce((n, j) => n + j.size, 0) / 1024 ** 3).toFixed(2)} GiB`);
if (process.argv.includes('--dry-run')) process.exit(0);
for (const name of ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET']) if (!process.env[name]) throw new Error(`Variável ausente: ${name}`);
const client = new S3Client({ region: 'auto', endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`, credentials: { accessKeyId: process.env.R2_ACCESS_KEY_ID, secretAccessKey: process.env.R2_SECRET_ACCESS_KEY }, requestChecksumCalculation: 'WHEN_REQUIRED', responseChecksumValidation: 'WHEN_REQUIRED' });
let next = 0, completed = 0, failed = 0;
async function worker() {
  while (next < jobs.length) {
    const job = jobs[next++];
    try {
      let exists = false;
      try { const head = await client.send(new HeadObjectCommand({ Bucket: process.env.R2_BUCKET, Key: job.key })); exists = head.ContentLength === job.size; }
      catch (e) { if (e.$metadata?.httpStatusCode !== 404) throw e; }
      if (!exists) await client.send(new PutObjectCommand({ Bucket: process.env.R2_BUCKET, Key: job.key, Body: createReadStream(job.path), ContentLength: job.size, ContentType: 'video/mp4' }));
      console.log(`${++completed}/${jobs.length} ${exists ? 'já existe' : 'enviado'} ${job.key}`);
    } catch (e) { failed++; console.error(`Falha em ${job.key}: ${e.message}`); }
  }
}
await Promise.all(Array.from({ length: 20 }, worker));
if (failed) { console.error(`${failed} envio(s) falharam`); process.exitCode = 1; }
