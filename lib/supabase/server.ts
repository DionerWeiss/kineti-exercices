import "server-only";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { supabaseEnv } from "@/lib/env";

/** Cliente Supabase com a sessão do usuário (cookies). Use em Server Components e Actions. */
export async function createClient() {
  // Dados por usuário vindos da rede: só na hora do pedido. Sem isso, o getClaims()
  // (que lê Date.now() para checar a validade do token) quebra a pré-busca em runtime.
  await connection();
  const cookieStore = await cookies();

  return createServerClient(supabaseEnv.url, supabaseEnv.key, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // Chamado de um Server Component: o proxy renova a sessão.
        }
      },
    },
  });
}
