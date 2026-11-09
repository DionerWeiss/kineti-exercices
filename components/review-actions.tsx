"use client";

import { useActionState, useState } from "react";
import { reviewVideo } from "@/app/actions/review";
import type { ReviewStatus } from "@/lib/exercises";

export function ReviewActions({ videoId, status }: { videoId: string; status: ReviewStatus }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [state, action, pending] = useActionState(
    async (prev: Awaited<ReturnType<typeof reviewVideo>>, formData: FormData) => {
      const result = await reviewVideo(prev, formData);
      if (result?.ok) {
        setRejecting(false);
        setReason("");
      }
      return result;
    },
    null,
  );

  if (rejecting) {
    return (
      <form action={action} className="space-y-2">
        <input type="hidden" name="videoId" value={videoId} />
        <input type="hidden" name="decision" value="rejected" />
        <label className="block text-sm font-medium" htmlFor={`reason-${videoId}`}>
          Motivo da reprovação
        </label>
        <textarea
          autoFocus
          id={`reason-${videoId}`}
          name="reason"
          required
          minLength={3}
          maxLength={2000}
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setRejecting(false);
          }}
          placeholder="Ex.: joelho atravessa o colchão no segundo 3; câmera corta os pés."
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-reject focus:ring-2 focus:ring-reject/20"
        />
        {state?.error ? (
          <p role="alert" className="text-sm text-reject">
            {state.error}
          </p>
        ) : null}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={pending || reason.trim().length < 3}
            className="rounded-lg bg-reject px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {pending ? "Salvando…" : "Confirmar reprovação"}
          </button>
          <button
            type="button"
            onClick={() => setRejecting(false)}
            className="rounded-lg px-3 py-1.5 text-sm text-muted hover:bg-surface-muted"
          >
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {status !== "approved" ? (
          <form action={action}>
            <input type="hidden" name="videoId" value={videoId} />
            <input type="hidden" name="decision" value="approved" />
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg bg-approve px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {pending ? "Salvando…" : "Aprovar"}
            </button>
          </form>
        ) : null}
        {status !== "rejected" ? (
          <button
            type="button"
            disabled={pending}
            onClick={() => setRejecting(true)}
            className="rounded-lg border border-reject/40 px-3 py-1.5 text-sm font-medium text-reject hover:bg-reject-soft disabled:opacity-50"
          >
            Reprovar
          </button>
        ) : null}
        {status !== "pending" ? (
          <form action={action}>
            <input type="hidden" name="videoId" value={videoId} />
            <input type="hidden" name="decision" value="pending" />
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg px-3 py-1.5 text-sm text-muted hover:bg-surface-muted disabled:opacity-50"
            >
              Desfazer revisão
            </button>
          </form>
        ) : null}
      </div>
      {state?.error ? (
        <p role="alert" className="text-sm text-reject">
          {state.error}
        </p>
      ) : null}
    </div>
  );
}
