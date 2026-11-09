#!/usr/bin/env node
// Importa os exercícios para o Supabase e, opcionalmente, liga os vídeos do manequim no R2.
//
// Exercícios: um por exercício do PocketPhysio atendido pelo manequim
// (mesmo nome + mesmo vídeo viram um só), mais os vídeos só do Kineti (sem PocketPhysio).
//
//   npm run seed                      # áreas + exercícios (upsert, pode rodar de novo)
//   npm run seed -- --videos          # liga cada exercício sem vídeo ao MP4 do manequim (versão 1)
//   npm run seed -- --prune           # apaga exercícios que saíram do catálogo (só se intocados)
//   npm run seed -- --dry-run         # só mostra o que faria
//
// Usa SUPABASE_SERVICE_ROLE_KEY (ignora RLS). Nunca exponha essa chave no app.

import { readFile, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { createClient } from "@supabase/supabase-js";
import { DeleteObjectsCommand, HeadObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

const ROOT = path.resolve(import.meta.dirname, "..");
const args = new Set(process.argv.slice(2));
const withVideos = args.has("--videos");
const prune = args.has("--prune");
const dryRun = args.has("--dry-run");
const SEED_EMAIL = "seed (pipeline do manequim)";

function env(name) {
  const value = process.env[name];
  if (!value) {
    console.error(`Falta a variável ${name} no .env.local`);
    process.exit(1);
  }
  return value;
}

function slugify(text) {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

// --- Monta o catálogo ---------------------------------------------------------

const catalog = JSON.parse(await readFile(path.join(ROOT, "tool/mannequin/catalog.json"), "utf8"));
const pocket = new Map(
  JSON.parse(await readFile(path.join(ROOT, "research/pocketphysio/exercicios.json"), "utf8")).map((e) => [e.id, e]),
);

const areas = catalog.areas.map((a, i) => ({ id: a.id, name: a.name, sort: i }));
const videos = new Map(catalog.exercises.map((v) => [v.slug, v]));

// Agrupa por (nome PT, vídeo).
const groups = new Map();
for (const video of catalog.exercises) {
  for (const id of video.pocketphysio) {
    const pp = pocket.get(id);
    if (!pp) throw new Error(`Id do PocketPhysio sem registro: ${id}`);
    const name = pp.nome_pt.trim();
    const key = `${name}\u0000${video.slug}`;
    if (!groups.has(key)) groups.set(key, { name, video, items: [] });
    groups.get(key).items.push(pp);
  }
}

const videosPerName = new Map();
for (const g of groups.values()) {
  videosPerName.set(g.name, (videosPerName.get(g.name) ?? 0) + 1);
}

const now = new Date().toISOString();
const exercises = [];
const used = new Set();
function uniqueSlug(base) {
  let slug = base;
  for (let n = 2; used.has(slug); n++) slug = `${base}-${n}`;
  used.add(slug);
  return slug;
}

// Vídeos só do Kineti mantêm o slug do vídeo.
for (const video of catalog.exercises.filter((v) => v.pocketphysio.length === 0)) {
  exercises.push({
    slug: uniqueSlug(video.slug),
    name: video.name,
    description: video.desc ?? "",
    focus: video.focus ?? "",
    area_id: video.area || null,
    props: video.props ?? "",
    camera_view: video.view ?? "",
    lib: video.lib ?? "",
    pocketphysio_ids: [],
    source: "kineti",
    video_slug: video.slug,
    video_name: video.name,
    updated_at: now,
  });
}

for (const g of groups.values()) {
  // Na fusão, fica a descrição mais completa.
  const main = g.items.reduce((a, b) => ((b.descricao_pt ?? "").length > (a.descricao_pt ?? "").length ? b : a));
  const base = videosPerName.get(g.name) > 1 ? `${slugify(g.name)}-${g.video.slug}` : slugify(g.name);
  exercises.push({
    slug: uniqueSlug(base),
    name: g.name,
    description: main.descricao_pt ?? "",
    focus: main.objetivo_pt ?? "",
    area_id: g.video.area || null,
    props: g.video.props ?? "",
    camera_view: g.video.view ?? "",
    lib: "pocketphysio",
    pocketphysio_ids: g.items.map((p) => p.id).sort(),
    source: "pocketphysio",
    video_slug: g.video.slug,
    video_name: g.video.name,
    updated_at: now,
  });
}

const merged = [...groups.values()].filter((g) => g.items.length > 1).length;
console.log(
  `Catálogo: ${areas.length} áreas, ${exercises.length} exercícios ` +
    `(${groups.size} do PocketPhysio, ${merged} deles fundidos; ${exercises.length - groups.size} só do Kineti), ` +
    `${videos.size} vídeos.`,
);

const supabase = createClient(env("NEXT_PUBLIC_SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
  auth: { persistSession: false },
});

/** O PostgREST devolve no máximo 1.000 linhas por vez. */
async function fetchAll(table, columns) {
  const rows = [];
  for (let from = 0; ; from += 1000) {
    const { data, error } = await supabase.from(table).select(columns).order("id").range(from, from + 999);
    if (error) throw error;
    rows.push(...data);
    if (data.length < 1000) return rows;
  }
}

let s3;
function r2() {
  s3 ??= new S3Client({
    region: "auto",
    endpoint: `https://${env("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId: env("R2_ACCESS_KEY_ID"), secretAccessKey: env("R2_SECRET_ACCESS_KEY") },
  });
  return s3;
}

// --- Grava áreas e exercícios ----------------------------------------------------

if (!dryRun) {
  const { error: areaError } = await supabase.from("areas").upsert(areas);
  if (areaError) throw areaError;
  for (let i = 0; i < exercises.length; i += 200) {
    const { error } = await supabase.from("exercises").upsert(exercises.slice(i, i + 200));
    if (error) throw error;
  }
  console.log("Áreas e exercícios gravados.");
}

// --- Remove o que saiu do catálogo -------------------------------------------

if (prune) {
  const wanted = new Set(exercises.map((e) => e.slug));
  const existing = [];
  for (let from = 0; ; from += 1000) {
    const { data, error } = await supabase.from("exercises").select("slug").order("slug").range(from, from + 999);
    if (error) throw error;
    existing.push(...data.map((r) => r.slug));
    if (data.length < 1000) break;
  }
  const stale = new Set(existing.filter((s) => !wanted.has(s)));
  const allVideos = await fetchAll("exercise_videos", "id, exercise_slug, r2_key, status, uploaded_by");
  const touched = new Set(
    allVideos.filter((v) => stale.has(v.exercise_slug) && (v.uploaded_by || v.status !== "pending")).map((v) => v.exercise_slug),
  );
  const removable = [...stale].filter((s) => !touched.has(s));
  console.log(`Prune: ${stale.size} fora do catálogo, ${removable.length} removíveis, ${touched.size} preservados (já revisados ou com upload).`);
  for (const slug of touched) console.log(`  preservado: ${slug}`);

  if (!dryRun && removable.length) {
    const removeSet = new Set(removable);
    const orphanCandidates = new Set(allVideos.filter((v) => removeSet.has(v.exercise_slug)).map((v) => v.r2_key));
    for (let i = 0; i < removable.length; i += 100) {
      const { error } = await supabase.from("exercises").delete().in("slug", removable.slice(i, i + 100));
      if (error) throw error;
    }
    // Apaga do R2 só os arquivos que nenhuma linha restante usa.
    const stillUsed = new Set(allVideos.filter((v) => !removeSet.has(v.exercise_slug)).map((v) => v.r2_key));
    const orphans = [...orphanCandidates].filter((k) => !stillUsed.has(k));
    for (let i = 0; i < orphans.length; i += 1000) {
      await r2().send(
        new DeleteObjectsCommand({
          Bucket: env("R2_BUCKET"),
          Delete: { Objects: orphans.slice(i, i + 1000).map((Key) => ({ Key })), Quiet: true },
        }),
      );
    }
    console.log(`  ${removable.length} exercícios e ${orphans.length} arquivos órfãos no R2 removidos.`);
  }
}

if (!withVideos) process.exit(0);

// --- Vídeos: um arquivo por vídeo do manequim, ligado a cada exercício ---------

const withVideo = new Set((await fetchAll("exercise_videos", "id, exercise_slug")).map((v) => v.exercise_slug));
const pending = exercises.filter((e) => !withVideo.has(e.slug));
const neededVideos = [...new Set(pending.map((e) => e.video_slug))];
const missingLocal = neededVideos.filter((s) => !existsSync(path.resolve(ROOT, videos.get(s).video)));

console.log(
  `Vídeos: ${pending.length} exercícios sem vídeo, usando ${neededVideos.length} arquivos do manequim ` +
    `(${missingLocal.length} ausentes no disco).`,
);
if (dryRun || pending.length === 0) process.exit(0);

const bucket = env("R2_BUCKET");
const keyFor = (videoSlug) => `mannequin/${videoSlug}.mp4`;
const sizes = new Map();

async function ensureObject(videoSlug) {
  const file = path.resolve(ROOT, videos.get(videoSlug).video);
  const key = keyFor(videoSlug);
  try {
    const head = await r2().send(new HeadObjectCommand({ Bucket: bucket, Key: key }));
    sizes.set(videoSlug, head.ContentLength);
    return;
  } catch (error) {
    if (error.$metadata?.httpStatusCode !== 404) throw error;
  }
  const [body, info] = await Promise.all([readFile(file), stat(file)]);
  await r2().send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body, ContentType: "video/mp4" }));
  sizes.set(videoSlug, info.size);
}

let failed = 0;
async function pool(items, size, fn) {
  const queue = [...items];
  let done = 0;
  await Promise.all(
    Array.from({ length: size }, async () => {
      while (queue.length) {
        const item = queue.shift();
        try {
          await fn(item);
        } catch (error) {
          failed++;
          console.error(`  ✗ ${item.exercise_slug ?? item}: ${error.message ?? error}`);
        }
        if (++done % 100 === 0 || done === items.length) console.log(`  ${done}/${items.length}`);
      }
    }),
  );
}

console.log("Enviando arquivos ao R2 (pula os que já existem)…");
await pool(neededVideos.filter((s) => !missingLocal.includes(s)), 6, ensureObject);

console.log("Ligando exercícios aos vídeos…");
const rows = pending
  .filter((e) => sizes.has(e.video_slug))
  .map((e) => ({
    exercise_slug: e.slug,
    r2_key: keyFor(e.video_slug),
    content_type: "video/mp4",
    size_bytes: sizes.get(e.video_slug),
    original_filename: path.basename(videos.get(e.video_slug).video),
    uploaded_by_email: SEED_EMAIL,
  }));
// Um insert por linha: o trigger numera a versão por exercício.
await pool(rows, 8, async (row) => {
  const { error } = await supabase.from("exercise_videos").insert(row);
  if (error) throw Object.assign(error, { slug: row.exercise_slug });
});

console.log(`Pronto: ${rows.length - failed} exercícios ligados a vídeos, ${failed} falhas.`);
process.exit(failed ? 1 : 0);
