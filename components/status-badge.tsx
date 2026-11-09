import type { ReviewState } from "@/lib/exercises";

const STYLES: Record<ReviewState, { label: string; className: string }> = {
  pending: { label: "Pendente", className: "bg-pending-soft text-pending" },
  approved: { label: "Aprovado", className: "bg-approve-soft text-approve" },
  rejected: { label: "Reprovado", className: "bg-reject-soft text-reject" },
  no_video: { label: "Sem vídeo", className: "bg-surface-muted text-muted" },
};

export function StatusBadge({ state }: { state: ReviewState }) {
  const { label, className } = STYLES[state];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
