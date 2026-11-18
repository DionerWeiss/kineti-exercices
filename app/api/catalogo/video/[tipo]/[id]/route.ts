import { videoUrl } from "@/lib/r2";
import { createClient } from "@/lib/supabase/server";

const prefixes: Record<string, string> = { manequim: "catalogo/manequim", lottie: "catalogo/lottie", render3d: "v10" };

export async function GET(_request: Request, { params }: { params: Promise<{ tipo: string; id: string }> }) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims?.sub) return new Response(null, { status: 401 });
  const { tipo, id } = await params;
  if (!Object.hasOwn(prefixes, tipo) || !/^[\w-]{1,200}$/.test(id)) return new Response(null, { status: 404 });
  return Response.redirect(await videoUrl(`${prefixes[tipo]}/${id}.mp4`), 307);
}
