import Link from "next/link";
import { ReviewActions } from "@/components/review-actions";
import { StatusBadge } from "@/components/status-badge";
import type { ExerciseWithVideo } from "@/lib/exercises";
import { formatDateTime } from "@/lib/format";

export function ExerciseCard({ exercise }: { exercise: ExerciseWithVideo }) {
  const e = exercise;
  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
      <div className="aspect-square bg-surface-muted">
        {e.video_url ? (
          <video
            src={e.video_url}
            controls
            loop
            muted
            playsInline
            preload="metadata"
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-muted">
            Ainda sem vídeo
            <Link
              href={`/upload?exercicio=${encodeURIComponent(e.slug)}`}
              className="rounded-lg bg-brand px-3 py-1.5 font-medium text-white hover:bg-brand-strong"
            >
              Enviar vídeo
            </Link>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="font-semibold leading-snug">
              <Link href={`/exercicios/${encodeURIComponent(e.slug)}`} className="hover:text-brand">
                {e.name}
              </Link>
            </h2>
            <p className="mt-0.5 text-xs text-muted">
              {e.area_name ?? "Sem área"}
              {e.version ? ` · versão ${e.version}` : ""}
              {e.version_count > 1 ? ` de ${e.version_count}` : ""}
            </p>
          </div>
          <StatusBadge state={e.review_state} />
        </div>

        <p className="text-sm text-foreground/80">{e.description}</p>
        {e.focus ? (
          <p className="text-xs text-muted">
            <span className="font-medium text-foreground/70">Foco:</span> {e.focus}
          </p>
        ) : null}

        {e.status === "rejected" && e.rejection_reason ? (
          <div className="rounded-lg bg-reject-soft px-3 py-2 text-sm text-reject">
            <p className="font-medium">Motivo da reprovação</p>
            <p className="whitespace-pre-line">{e.rejection_reason}</p>
            <p className="mt-1 text-xs opacity-80">
              {e.reviewed_by_email} · {formatDateTime(e.reviewed_at)}
            </p>
          </div>
        ) : null}
        {e.status === "approved" ? (
          <p className="text-xs text-approve">
            Aprovado por {e.reviewed_by_email ?? "—"} em {formatDateTime(e.reviewed_at)}
          </p>
        ) : null}

        <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
          {e.video_id && e.status ? (
            <ReviewActions videoId={e.video_id} status={e.status} />
          ) : (
            <span className="text-xs text-muted">Nada para revisar</span>
          )}
          {e.status === "rejected" ? (
            <Link
              href={`/upload?exercicio=${encodeURIComponent(e.slug)}`}
              className="text-sm font-medium text-brand hover:underline"
            >
              Enviar nova versão
            </Link>
          ) : null}
        </div>
      </div>
    </article>
  );
}
