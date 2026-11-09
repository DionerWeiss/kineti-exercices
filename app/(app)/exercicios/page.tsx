import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AutoSubmitSelect } from "@/components/auto-submit-select";
import { ExerciseCard } from "@/components/exercise-card";
import {
  PAGE_SIZE,
  REVIEW_STATES,
  listAreas,
  listExercises,
  parseFilters,
  type ListFilters,
} from "@/lib/exercises";

export const metadata: Metadata = { title: "Exercícios" };

export default function ExercisesPage({ searchParams }: PageProps<"/exercicios">) {
  return (
    <>
      <h1 className="text-2xl font-semibold">Exercícios</h1>
      <p className="mt-1 text-sm text-muted">
        Assista à versão mais recente de cada vídeo e aprove ou reprove. Reprovar exige o motivo.
      </p>
      <Suspense fallback={<ListSkeleton />}>
        <ExerciseList searchParams={searchParams} />
      </Suspense>
    </>
  );
}

function toQuery(filters: ListFilters, patch: Partial<ListFilters>) {
  const next = { ...filters, ...patch };
  const params = new URLSearchParams();
  params.set("status", next.state);
  if (next.area) params.set("area", next.area);
  if (next.q) params.set("q", next.q);
  if (next.video) params.set("video", next.video);
  if (next.page > 1) params.set("pagina", String(next.page));
  return `/exercicios?${params}`;
}

async function ExerciseList({ searchParams }: { searchParams: PageProps<"/exercicios">["searchParams"] }) {
  const filters = parseFilters(await searchParams);
  const [areas, { exercises, total, counts }] = await Promise.all([
    listAreas(),
    listExercises(filters),
  ]);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mt-6 space-y-5">
      <nav aria-label="Status" className="flex flex-wrap gap-2">
        {REVIEW_STATES.map((s) => {
          const active = s.value === filters.state;
          return (
            <Link
              key={s.value}
              href={toQuery(filters, { state: s.value, page: 1 })}
              aria-current={active ? "page" : undefined}
              className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                active
                  ? "border-ink bg-ink text-white"
                  : "border-border bg-surface text-foreground/80 hover:border-foreground/30"
              }`}
            >
              {s.label}
              <span className={`ml-1.5 tabular-nums ${active ? "text-white/70" : "text-muted"}`}>
                {counts[s.value]}
              </span>
            </Link>
          );
        })}
      </nav>

      {filters.video ? (
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <span className="rounded-full bg-brand-soft px-3 py-1 text-brand">
            Exercícios que usam o vídeo <span className="font-mono">{filters.video}</span>
          </span>
          <Link href={toQuery(filters, { video: null, page: 1 })} className="text-muted hover:underline">
            limpar
          </Link>
        </p>
      ) : null}

      <form action="/exercicios" className="flex flex-wrap gap-2">
        <input type="hidden" name="status" value={filters.state} />
        {filters.video ? <input type="hidden" name="video" value={filters.video} /> : null}
        <input type="hidden" name="pagina" value="1" />
        <input
          type="search"
          name="q"
          defaultValue={filters.q ?? ""}
          placeholder="Buscar por nome ou descrição"
          className="min-w-56 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
        />
        <AutoSubmitSelect
          name="area"
          defaultValue={filters.area ?? ""}
          aria-label="Área"
          className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
        >
          <option value="">Todas as áreas</option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </AutoSubmitSelect>
        <button
          type="submit"
          className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Buscar
        </button>
      </form>

      {exercises.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center text-muted">
          {filters.state === "pending"
            ? "Nenhum vídeo esperando revisão com esses filtros."
            : "Nenhum exercício encontrado com esses filtros."}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {exercises.map((e) => (
            <ExerciseCard key={`${e.slug}-${e.video_id ?? "none"}`} exercise={e} />
          ))}
        </div>
      )}

      {pages > 1 ? (
        <nav aria-label="Paginação" className="flex items-center justify-center gap-3 text-sm">
          <PageLink href={toQuery(filters, { page: filters.page - 1 })} disabled={filters.page <= 1}>
            ← Anterior
          </PageLink>
          <span className="tabular-nums text-muted">
            Página {filters.page} de {pages} · {total} exercícios
          </span>
          <PageLink href={toQuery(filters, { page: filters.page + 1 })} disabled={filters.page >= pages}>
            Próxima →
          </PageLink>
        </nav>
      ) : null}
    </div>
  );
}

function PageLink({ href, disabled, children }: { href: string; disabled: boolean; children: React.ReactNode }) {
  if (disabled) {
    return <span className="rounded-lg px-3 py-1.5 text-muted/50">{children}</span>;
  }
  return (
    <Link href={href} className="rounded-lg border border-border bg-surface px-3 py-1.5 hover:border-foreground/30">
      {children}
    </Link>
  );
}

function ListSkeleton() {
  return (
    <div className="mt-6 space-y-5" aria-busy="true">
      <div className="flex gap-2">
        {REVIEW_STATES.map((s) => (
          <div key={s.value} className="h-8 w-24 animate-pulse rounded-full bg-surface-muted" />
        ))}
      </div>
      <div className="h-10 animate-pulse rounded-lg bg-surface-muted" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="h-96 animate-pulse rounded-xl bg-surface-muted" />
        ))}
      </div>
    </div>
  );
}
