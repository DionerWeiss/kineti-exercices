"use server";

import { refresh } from "next/cache";
import { requireUser } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

export type ReviewState = { ok: boolean; error?: string } | null;

const MIN_REASON = 3;
const MAX_REASON = 2000;

export async function reviewVideo(_prev: ReviewState, formData: FormData): Promise<ReviewState> {
  await requireUser();

  const videoId = String(formData.get("videoId") ?? "");
  const decision = String(formData.get("decision") ?? "");
  const reason = String(formData.get("reason") ?? "").trim();

  if (!videoId) return { ok: false, error: "Vídeo não informado." };
  if (decision !== "approved" && decision !== "rejected" && decision !== "pending") {
    return { ok: false, error: "Decisão inválida." };
  }
  if (decision === "rejected") {
    if (reason.length < MIN_REASON) {
      return { ok: false, error: "Escreva o motivo da reprovação." };
    }
    if (reason.length > MAX_REASON) {
      return { ok: false, error: `O motivo pode ter até ${MAX_REASON} caracteres.` };
    }
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("exercise_videos")
    .update({ status: decision, rejection_reason: decision === "rejected" ? reason : null })
    .eq("id", videoId)
    .select("id");

  if (error) return { ok: false, error: `Não foi possível salvar: ${error.message}` };
  if (!data?.length) return { ok: false, error: "Vídeo não encontrado." };

  refresh();
  return { ok: true };
}
