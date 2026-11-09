import "server-only";
import { createClient } from "@/lib/supabase/server";
import { videoUrl } from "@/lib/r2";

export type ReviewStatus = "pending" | "approved" | "rejected";
export type ReviewState = ReviewStatus | "no_video";

export const REVIEW_STATES: { value: ReviewState | "all"; label: string }[] = [
  { value: "pending", label: "Pendentes" },
  { value: "rejected", label: "Reprovados" },
  { value: "approved", label: "Aprovados" },
  { value: "no_video", label: "Sem vídeo" },
  { value: "all", label: "Todos" },
];

export const PAGE_SIZE = 12;

export type ExerciseRow = {
  slug: string;
  name: string;
  description: string;
  focus: string;
  area_id: string | null;
  area_name: string | null;
  props: string;
  camera_view: string;
  video_id: string | null;
  version: number | null;
  r2_key: string | null;
  status: ReviewStatus | null;
  rejection_reason: string | null;
  uploaded_at: string | null;
  uploaded_by_email: string | null;
  reviewed_at: string | null;
  reviewed_by_email: string | null;
  review_state: ReviewState;
  version_count: number;
};

export type ExerciseWithVideo = ExerciseRow & { video_url: string | null };

export type VideoVersion = {
  id: string;
  version: number;
  r2_key: string;
  content_type: string;
  size_bytes: number;
  original_filename: string | null;
  uploaded_at: string;
  uploaded_by_email: string | null;
  status: ReviewStatus;
  rejection_reason: string | null;
  reviewed_at: string | null;
  reviewed_by_email: string | null;
  video_url: string;
};

export type ListFilters = {
  state: ReviewState | "all";
  area: string | null;
  q: string | null;
  page: number;
};

export function parseFilters(params: Record<string, string | string[] | undefined>): ListFilters {
  const one = (k: string) => {
    const v = params[k];
    return (Array.isArray(v) ? v[0] : v)?.trim() || null;
  };
  const rawState = one("status");
  const state = REVIEW_STATES.some((s) => s.value === rawState)
    ? (rawState as ListFilters["state"])
    : "pending";
  const page = Math.max(1, Number.parseInt(one("pagina") ?? "1", 10) || 1);
  return { state, area: one("area"), q: one("q"), page };
}

// Remove curingas do ILIKE e caracteres que quebram o filtro `or` do PostgREST.
function likePattern(q: string) {
  const clean = q.replace(/[\\%_*,()"]/g, " ").replace(/\s+/g, " ").trim();
  return `%${clean.replace(/ /g, "%")}%`;
}

export async function listAreas() {
  const supabase = await createClient();
  const { data, error } = await supabase.from("areas").select("id, name").order("sort");
  if (error) throw error;
  return data;
}

export async function listExercises(filters: ListFilters) {
  const supabase = await createClient();

  const base = () => {
    let query = supabase.from("exercise_review_list").select("*", { count: "exact" });
    if (filters.area) query = query.eq("area_id", filters.area);
    if (filters.q) {
      const p = likePattern(filters.q);
      query = query.or(`name.ilike.${p},description.ilike.${p},slug.ilike.${p}`);
    }
    return query;
  };

  const from = (filters.page - 1) * PAGE_SIZE;
  let listQuery = base();
  if (filters.state !== "all") listQuery = listQuery.eq("review_state", filters.state);
  const list = listQuery
    .order("uploaded_at", { ascending: true, nullsFirst: false })
    .order("name")
    .range(from, from + PAGE_SIZE - 1);

  const countFor = async (state: ReviewState) => {
    const { count, error } = await base().eq("review_state", state).limit(0);
    if (error) throw error;
    return count ?? 0;
  };

  const [{ data, count, error }, pending, rejected, approved, noVideo] = await Promise.all([
    list,
    countFor("pending"),
    countFor("rejected"),
    countFor("approved"),
    countFor("no_video"),
  ]);
  if (error) throw error;

  const rows = (data ?? []) as ExerciseRow[];
  const exercises: ExerciseWithVideo[] = await Promise.all(
    rows.map(async (row) => ({
      ...row,
      video_url: row.r2_key ? await videoUrl(row.r2_key) : null,
    })),
  );

  return {
    exercises,
    total: count ?? 0,
    counts: {
      pending,
      rejected,
      approved,
      no_video: noVideo,
      all: pending + rejected + approved + noVideo,
    } satisfies Record<ReviewState | "all", number>,
  };
}

export async function getExercise(slug: string) {
  const supabase = await createClient();
  const [{ data: exercise, error }, { data: versions, error: vError }] = await Promise.all([
    supabase.from("exercise_review_list").select("*").eq("slug", slug).maybeSingle(),
    supabase
      .from("exercise_videos")
      .select(
        "id, version, r2_key, content_type, size_bytes, original_filename, uploaded_at, uploaded_by_email, status, rejection_reason, reviewed_at, reviewed_by_email",
      )
      .eq("exercise_slug", slug)
      .order("version", { ascending: false }),
  ]);
  if (error) throw error;
  if (vError) throw vError;
  if (!exercise) return null;

  const withUrls: VideoVersion[] = await Promise.all(
    (versions ?? []).map(async (v) => ({ ...v, video_url: await videoUrl(v.r2_key) })),
  );
  return { exercise: exercise as ExerciseRow, versions: withUrls };
}

/** Lista enxuta para o seletor da tela de upload. */
export async function listExerciseOptions() {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("exercise_review_list")
    .select("slug, name, area_name, review_state, version_count")
    .order("name")
    .range(0, 4999);
  if (error) throw error;
  return data as Pick<ExerciseRow, "slug" | "name" | "area_name" | "review_state" | "version_count">[];
}
