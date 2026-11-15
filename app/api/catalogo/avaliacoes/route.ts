import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const { data: auth } = await supabase.auth.getClaims();
  if (!auth?.claims?.sub) return new Response(null, { status: 401 });
  const reviews = [];
  for (let from = 0; ; from += 1000) {
    const { data, error } = await supabase.from("catalog_reviews").select("exercise_id,note,choice").eq("user_id", auth.claims.sub).order("exercise_id").range(from, from + 999);
    if (error) return new Response("Erro ao carregar avaliações", { status: 500 });
    reviews.push(...data);
    if (data.length < 1000) break;
  }
  return Response.json(reviews);
}

export async function PUT(request: Request) {
  const supabase = await createClient();
  const { data: auth } = await supabase.auth.getClaims();
  if (!auth?.claims?.sub) return new Response(null, { status: 401 });
  let input;
  try { input = await request.json(); } catch { return new Response(null, { status: 400 }); }
  if (typeof input.exercise_id !== "string" || !/^[\w-]{1,200}$/.test(input.exercise_id) || typeof input.note !== "string" || input.note.length > 10000 || ![null, "manequim", "lottie", "render3d"].includes(input.choice)) return new Response(null, { status: 400 });
  const { error } = await supabase.from("catalog_reviews").upsert({ user_id: auth.claims.sub, exercise_id: input.exercise_id, note: input.note, choice: input.choice, updated_at: new Date().toISOString() });
  return new Response(null, { status: error ? 500 : 204 });
}
