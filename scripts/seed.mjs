#!/usr/bin/env node
// Importa o catálogo do manequim para o Supabase e, opcionalmente, sobe os vídeos para o R2.
//
//   npm run seed                 # áreas + exercícios (upsert, pode rodar de novo)
//   npm run seed -- --videos     # também sobe os MP4 locais como versão 1 dos exercícios sem vídeo
//   npm run seed -- --dry-run    # só mostra o que faria
//
// Usa SUPABASE_SERVICE_ROLE_KEY (ignora RLS). Nunca exponha essa chave no app.

import { readFile, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createClient } from "@supabase/supabase-js";
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

const ROOT = path.resolve(import.meta.dirname, "..");
const args = new Set(process.argv.slice(2));
const withVideos = args.has("--videos");
const dryRun = args.has("--dry-run");
const catalogArg = process.argv.find((a) => a.startsWith("--catalog="));
const catalogPath = path.resolve(ROOT, catalogArg?.split("=")[1] ?? "tool/mannequin/catalog.json");

function env(name) {
  const value = process.env[name];
  if (!value) {
    console.error(`Falta a variável ${name} no .env.local`);
    process.exit(1);
  }
  return value;
}

const catalog = JSON.parse(await readFile(catalogPath, "utf8"));
const areas = catalog.areas.map((a, i) => ({ id: a.id, name: a.name, sort: i }));
const exercises = catalog.exercises.map((e) => ({
  slug: e.slug,
  name: e.name,
  description: e.desc ?? "",
  focus: e.focus ?? "",
  area_id: e.area || null,
  props: e.props ?? "",
  camera_view: e.view ?? "",
  lib: e.lib ?? "",
  pocketphysio_ids: e.pocketphysio ?? [],
  updated_at: new Date().toISOString(),
}));

console.log(`Catálogo: ${areas.length} áreas, ${exercises.length} exercícios (${path.relative(ROOT, catalogPath)})`);
if (dryRun && !withVideos) process.exit(0);

const supabase = createClient(env("NEXT_PUBLIC_SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
  auth: { persistSession: false },
});

if (!dryRun) {
  const { error: areaError } = await supabase.from("areas").upsert(areas);
  if (areaError) throw areaError;
  for (let i = 0; i < exercises.length; i += 200) {
    const { error } = await supabase.from("exercises").upsert(exercises.slice(i, i + 200));
    if (error) throw error;
  }
  console.log("Áreas e exercícios gravados.");
}

if (!withVideos) process.exit(0);

// --- Vídeos -----------------------------------------------------------------

const { data: existing, error: existingError } = await supabase
  .from("exercise_videos")
  .select("exercise_slug")
  .range(0, 9999);
if (existingError) throw existingError;
const hasVideo = new Set(existing.map((v) => v.exercise_slug));

const todo = catalog.exercises
  .filter((e) => e.video && !hasVideo.has(e.slug))
  .map((e) => ({ slug: e.slug, file: path.resolve(ROOT, e.video) }))
  .filter((e) => existsSync(e.file));

const missing = catalog.exercises.filter((e) => e.video && !existsSync(path.resolve(ROOT, e.video)));
console.log(
  `Vídeos: ${todo.length} para enviar, ${hasVideo.size} exercícios já têm vídeo, ${missing.length} arquivos locais ausentes.`,
);
if (dryRun || todo.length === 0) process.exit(0);

const bucket = env("R2_BUCKET");
const s3 = new S3Client({
  region: "auto",
  endpoint: `https://${env("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId: env("R2_ACCESS_KEY_ID"), secretAccessKey: env("R2_SECRET_ACCESS_KEY") },
});

let done = 0;
let failed = 0;
async function upload({ slug, file }) {
  const key = `exercises/${slug}/${randomUUID()}.mp4`;
  try {
    const [body, info] = await Promise.all([readFile(file), stat(file)]);
    await s3.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body, ContentType: "video/mp4" }));
    const { error } = await supabase.from("exercise_videos").insert({
      exercise_slug: slug,
      r2_key: key,
      content_type: "video/mp4",
      size_bytes: info.size,
      original_filename: path.basename(file),
      uploaded_by_email: "seed (pipeline do manequim)",
    });
    if (error) throw error;
  } catch (error) {
    failed++;
    console.error(`  ✗ ${slug}: ${error.message ?? error}`);
  }
  done++;
  if (done % 25 === 0 || done === todo.length) console.log(`  ${done}/${todo.length}`);
}

const queue = [...todo];
await Promise.all(
  Array.from({ length: 6 }, async () => {
    while (queue.length) await upload(queue.shift());
  }),
);
console.log(`Pronto: ${done - failed} enviados, ${failed} falhas.`);
process.exit(failed ? 1 : 0);
