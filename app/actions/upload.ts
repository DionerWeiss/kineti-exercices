"use server";

import { refresh } from "next/cache";
import { requireUser } from "@/lib/auth";
import { deleteObject, headObject, presignUpload } from "@/lib/r2";
import { createClient } from "@/lib/supabase/server";
import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES, VIDEO_EXTENSIONS } from "@/lib/upload-rules";

type Result<T> = ({ ok: true } & T) | { ok: false; error: string };

function keyPrefix(slug: string) {
  return `exercises/${slug}/`;
}

/** Passo 1: valida o pedido e devolve uma URL assinada para o navegador enviar ao R2. */
export async function createUploadUrl(input: {
  slug: string;
  contentType: string;
  size: number;
}): Promise<Result<{ key: string; url: string }>> {
  await requireUser();

  const ext = VIDEO_EXTENSIONS[input.contentType];
  if (!ext) return { ok: false, error: "Formato não aceito. Envie MP4, WebM ou MOV." };
  if (!(input.size > 0)) return { ok: false, error: "Arquivo vazio." };
  if (input.size > MAX_UPLOAD_BYTES) return { ok: false, error: "Arquivo maior que 1 GB." };

  const supabase = await createClient();
  const { data: exercise, error } = await supabase
    .from("exercises")
    .select("slug")
    .eq("slug", input.slug)
    .maybeSingle();
  if (error) return { ok: false, error: error.message };
  if (!exercise) return { ok: false, error: "Exercício não encontrado." };

  const key = `${keyPrefix(exercise.slug)}${crypto.randomUUID()}.${ext}`;
  const url = await presignUpload(key, input.contentType);
  return { ok: true, key, url };
}

/** Passo 2: depois do PUT, confere o objeto no R2 e registra a nova versão. */
export async function confirmUpload(input: {
  slug: string;
  key: string;
  originalFilename: string;
}): Promise<Result<{ version: number }>> {
  await requireUser();

  const prefix = keyPrefix(input.slug);
  const tail = input.key.slice(prefix.length);
  if (!input.key.startsWith(prefix) || !/^[0-9a-f-]{36}\.(mp4|webm|mov)$/.test(tail)) {
    return { ok: false, error: "Chave de upload inválida." };
  }

  const head = await headObject(input.key);
  if (!head) return { ok: false, error: "O arquivo não chegou ao R2. Tente enviar de novo." };
  if (head.size > MAX_UPLOAD_BYTES || !ACCEPTED_TYPES.includes(head.contentType)) {
    await deleteObject(input.key);
    return { ok: false, error: "Arquivo recusado (tamanho ou formato)." };
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("exercise_videos")
    .insert({
      exercise_slug: input.slug,
      r2_key: input.key,
      content_type: head.contentType,
      size_bytes: head.size,
      original_filename: input.originalFilename.slice(0, 255),
    })
    .select("version")
    .single();

  if (error) {
    // Chave repetida = confirmação em dobro; o registro já existe.
    if (error.code !== "23505") await deleteObject(input.key);
    return { ok: false, error: `Não foi possível registrar o vídeo: ${error.message}` };
  }

  refresh();
  return { ok: true, version: data.version };
}
