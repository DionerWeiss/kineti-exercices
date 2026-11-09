"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { confirmUpload, createUploadUrl } from "@/app/actions/upload";
import { StatusBadge } from "@/components/status-badge";
import type { ExerciseOption } from "@/lib/exercises";
import { formatBytes } from "@/lib/format";
import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES } from "@/lib/upload-rules";

type Option = ExerciseOption;

type Phase =
  | { kind: "idle" }
  | { kind: "uploading"; progress: number }
  | { kind: "saving" }
  | { kind: "done"; slug: string; name: string; version: number }
  | { kind: "error"; message: string };

function normalize(text: string) {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

/** PUT direto no R2 com progresso (fetch ainda não expõe progresso de upload). */
function putWithProgress(url: string, file: File, onProgress: (ratio: number) => void) {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`O R2 recusou o envio (HTTP ${xhr.status}).`));
    xhr.onerror = () =>
      reject(new Error("Falha de rede ao enviar. Confira a regra de CORS do bucket R2."));
    xhr.send(file);
  });
}

export function UploadForm({ options, initialSlug }: { options: Option[]; initialSlug: string | null }) {
  const [slug, setSlug] = useState<string | null>(
    options.some((o) => o.slug === initialSlug) ? initialSlug : null,
  );
  const [query, setQuery] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const fileInput = useRef<HTMLInputElement>(null);

  const selected = options.find((o) => o.slug === slug) ?? null;
  const busy = phase.kind === "uploading" || phase.kind === "saving";

  const matches = useMemo(() => {
    const q = normalize(query.trim());
    const list = q
      ? options.filter((o) => normalize(`${o.name} ${o.area_name ?? ""} ${o.video_name ?? ""} ${o.slug}`).includes(q))
      : options;
    return list.slice(0, 50);
  }, [options, query]);

  function pickFile(next: File | undefined) {
    if (!next) return;
    if (!ACCEPTED_TYPES.includes(next.type)) {
      setPhase({ kind: "error", message: "Formato não aceito. Envie MP4, WebM ou MOV." });
      return;
    }
    if (next.size > MAX_UPLOAD_BYTES) {
      setPhase({ kind: "error", message: "Arquivo maior que 1 GB." });
      return;
    }
    setFile(next);
    setPhase({ kind: "idle" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !file) return;

    setPhase({ kind: "uploading", progress: 0 });
    try {
      const ticket = await createUploadUrl({
        slug: selected.slug,
        contentType: file.type,
        size: file.size,
      });
      if (!ticket.ok) throw new Error(ticket.error);

      await putWithProgress(ticket.url, file, (progress) =>
        setPhase({ kind: "uploading", progress }),
      );

      setPhase({ kind: "saving" });
      const saved = await confirmUpload({
        slug: selected.slug,
        key: ticket.key,
        originalFilename: file.name,
      });
      if (!saved.ok) throw new Error(saved.error);

      setPhase({ kind: "done", slug: selected.slug, name: selected.name, version: saved.version });
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (error) {
      setPhase({
        kind: "error",
        message: error instanceof Error ? error.message : "Erro inesperado no envio.",
      });
    }
  }

  return (
    <form onSubmit={submit} className="mt-6 grid gap-6 lg:grid-cols-2">
      <section className="rounded-xl border border-border bg-surface p-4 shadow-sm">
        <h2 className="font-semibold">1. Exercício</h2>
        {selected ? (
          <div className="mt-3 flex items-start justify-between gap-3 rounded-lg bg-brand-soft p-3">
            <div>
              <p className="font-medium">{selected.name}</p>
              <p className="text-xs text-muted">
                {selected.area_name ?? "Sem área"} ·{" "}
                {selected.version_count === 0
                  ? "primeiro vídeo"
                  : `vai virar a versão ${selected.version_count + 1}`}
              </p>
              {selected.shared_count > 1 ? (
                <p className="mt-1 text-xs text-muted">
                  Hoje usa o vídeo “{selected.video_name}”, junto com mais {selected.shared_count - 1}. O envio
                  novo vale só para este exercício.
                </p>
              ) : null}
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() => setSlug(null)}
              className="text-sm text-brand hover:underline disabled:opacity-50"
            >
              Trocar
            </button>
          </div>
        ) : (
          <>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Buscar entre ${options.length} exercícios`}
              aria-label="Buscar exercício"
              className="mt-3 w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
            />
            <ul className="mt-2 max-h-96 divide-y divide-border overflow-y-auto rounded-lg border border-border">
              {matches.map((o) => (
                <li key={o.slug}>
                  <button
                    type="button"
                    onClick={() => setSlug(o.slug)}
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-surface-muted"
                  >
                    <span>
                      <span className="block">{o.name}</span>
                      <span className="block text-xs text-muted">{o.area_name ?? "Sem área"}</span>
                    </span>
                    <StatusBadge state={o.review_state} />
                  </button>
                </li>
              ))}
              {matches.length === 0 ? (
                <li className="px-3 py-6 text-center text-sm text-muted">Nenhum exercício encontrado.</li>
              ) : null}
            </ul>
          </>
        )}
      </section>

      <section className="flex flex-col rounded-xl border border-border bg-surface p-4 shadow-sm">
        <h2 className="font-semibold">2. Vídeo</h2>
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pickFile(e.dataTransfer.files[0]);
          }}
          className={`mt-3 flex min-h-40 cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed px-4 py-8 text-center text-sm transition-colors ${
            dragging ? "border-brand bg-brand-soft" : "border-border hover:border-foreground/30"
          }`}
        >
          <input
            ref={fileInput}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            disabled={busy}
            onChange={(e) => pickFile(e.target.files?.[0])}
            className="sr-only"
          />
          {file ? (
            <>
              <span className="font-medium">{file.name}</span>
              <span className="text-muted">{formatBytes(file.size)} · clique para trocar</span>
            </>
          ) : (
            <>
              <span className="font-medium">Arraste o vídeo aqui ou clique para escolher</span>
              <span className="text-muted">MP4, WebM ou MOV, até 1 GB</span>
            </>
          )}
        </label>

        <div className="mt-4 space-y-3">
          {phase.kind === "uploading" ? (
            <div>
              <div
                className="h-2 overflow-hidden rounded-full bg-surface-muted"
                role="progressbar"
                aria-valuenow={Math.round(phase.progress * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full bg-brand transition-[width]"
                  style={{ width: `${phase.progress * 100}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-muted tabular-nums">
                Enviando… {Math.round(phase.progress * 100)}%
              </p>
            </div>
          ) : null}
          {phase.kind === "saving" ? <p className="text-sm text-muted">Registrando a versão…</p> : null}
          {phase.kind === "error" ? (
            <p role="alert" className="rounded-lg bg-reject-soft px-3 py-2 text-sm text-reject">
              {phase.message}
            </p>
          ) : null}
          {phase.kind === "done" ? (
            <p role="status" className="rounded-lg bg-approve-soft px-3 py-2 text-sm text-approve">
              Versão {phase.version} de “{phase.name}” enviada.{" "}
              <Link href={`/exercicios/${encodeURIComponent(phase.slug)}`} className="font-medium underline">
                Ver exercício
              </Link>
            </p>
          ) : null}

          <button
            type="submit"
            disabled={!selected || !file || busy}
            className="w-full rounded-lg bg-brand px-4 py-2 font-medium text-white hover:bg-brand-strong disabled:opacity-50"
          >
            {busy ? "Enviando…" : "Enviar vídeo"}
          </button>
        </div>
      </section>
    </form>
  );
}
