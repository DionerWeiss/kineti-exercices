import "server-only";

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Variável de ambiente ausente: ${name} (veja .env.example)`);
  }
  return value;
}

export const supabaseEnv = {
  get url() {
    return required("NEXT_PUBLIC_SUPABASE_URL");
  },
  get key() {
    return required("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY");
  },
};

export const r2Env = {
  get accountId() {
    return required("R2_ACCOUNT_ID");
  },
  get accessKeyId() {
    return required("R2_ACCESS_KEY_ID");
  },
  get secretAccessKey() {
    return required("R2_SECRET_ACCESS_KEY");
  },
  get bucket() {
    return required("R2_BUCKET");
  },
  /** Domínio público do bucket (opcional). Sem ele, os vídeos usam URL assinada. */
  get publicUrl() {
    return process.env.R2_PUBLIC_URL?.replace(/\/+$/, "") || null;
  },
};
