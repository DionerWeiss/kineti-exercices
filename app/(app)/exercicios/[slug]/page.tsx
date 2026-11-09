import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ReviewActions } from "@/components/review-actions";
import { StatusBadge } from "@/components/status-badge";
import { getExercise } from "@/lib/exercises";
import { formatBytes, formatDateTime } from "@/lib/format";

export default function ExercisePage({ params }: PageProps<"/exercicios/[slug]">) {
  return (
    <>
      <Link href="/exercicios" className="text-sm text-brand hover:underline">
        ← Exercícios
      </Link>
      <Suspense fallback={<div className="mt-4 h-96 animate-pulse rounded-xl bg-surface-muted" />}>
        <ExerciseDetail params={params} />
      </Suspense>
    </>
  );
}

async function ExerciseDetail({ params }: { params: PageProps<"/exercicios/[slug]">["params"] }) {
  const { slug } = await params;
  const result = await getExercise(decodeURIComponent(slug));
  if (!result) notFound();
  const { exercise: e, versions } = result;

  return (
    <div className="mt-4 space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{e.name}</h1>
            <StatusBadge state={e.review_state} />
          </div>
          <p className="mt-1 text-sm text-muted">
            {e.area_name ?? "Sem área"}
            {e.props ? ` · ${e.props}` : ""}
            {e.camera_view ? ` · câmera ${e.camera_view}` : ""}
          </p>
          <p className="mt-3">{e.description}</p>
          {e.focus ? (
            <p className="mt-2 text-sm text-muted">
              <span className="font-medium text-foreground/70">Foco:</span> {e.focus}
            </p>
          ) : null}
          {e.video_slug ? (
            <p className="mt-2 text-sm text-muted">
              Vídeo do manequim: <span className="font-medium text-foreground/80">{e.video_name}</span>
              {e.shared_count > 1 ? (
                <>
                  {" · "}
                  <Link
                    href={`/exercicios?status=all&video=${encodeURIComponent(e.video_slug)}`}
                    className="text-brand hover:underline"
                  >
                    usado por mais {e.shared_count - 1}
                  </Link>
                </>
              ) : null}
            </p>
          ) : null}
          <p className="mt-2 font-mono text-xs text-muted">
            {e.slug}
            {e.pocketphysio_ids.length
              ? ` · PocketPhysio ${e.pocketphysio_ids.length > 1 ? `(${e.pocketphysio_ids.length} fundidos)` : ""} ${e.pocketphysio_ids.join(", ")}`
              : ""}
          </p>
        </div>
        <Link
          href={`/upload?exercicio=${encodeURIComponent(e.slug)}`}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-strong"
        >
          Enviar nova versão
        </Link>
      </header>

      <section>
        <h2 className="text-lg font-semibold">
          Versões <span className="font-normal text-muted">({versions.length})</span>
        </h2>
        {versions.length === 0 ? (
          <p className="mt-3 rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center text-muted">
            Nenhum vídeo enviado ainda.
          </p>
        ) : (
          <ol className="mt-3 space-y-4">
            {versions.map((v, i) => (
              <li
                key={v.id}
                className="grid gap-4 rounded-xl border border-border bg-surface p-4 shadow-sm md:grid-cols-[minmax(0,320px)_1fr]"
              >
                <video
                  src={v.video_url}
                  controls
                  loop
                  muted
                  playsInline
                  preload="metadata"
                  className="aspect-square w-full rounded-lg bg-surface-muted object-contain"
                />
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">Versão {v.version}</h3>
                    {i === 0 ? (
                      <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs text-brand">atual</span>
                    ) : null}
                    <StatusBadge state={v.status} />
                  </div>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                    <dt className="text-muted">Enviado</dt>
                    <dd>
                      {formatDateTime(v.uploaded_at)}
                      {v.uploaded_by_email ? ` por ${v.uploaded_by_email}` : ""}
                    </dd>
                    <dt className="text-muted">Arquivo</dt>
                    <dd className="truncate">
                      {v.original_filename ?? v.r2_key.split("/").pop()} · {formatBytes(v.size_bytes)}
                    </dd>
                    {v.reviewed_at ? (
                      <>
                        <dt className="text-muted">Revisado</dt>
                        <dd>
                          {formatDateTime(v.reviewed_at)}
                          {v.reviewed_by_email ? ` por ${v.reviewed_by_email}` : ""}
                        </dd>
                      </>
                    ) : null}
                  </dl>
                  {v.status === "rejected" && v.rejection_reason ? (
                    <div className="rounded-lg bg-reject-soft px-3 py-2 text-sm text-reject">
                      <p className="font-medium">Motivo da reprovação</p>
                      <p className="whitespace-pre-line">{v.rejection_reason}</p>
                    </div>
                  ) : null}
                  <div className="mt-auto border-t border-border pt-3">
                    <ReviewActions videoId={v.id} status={v.status} />
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
