import type { Metadata } from "next";
import { Suspense } from "react";
import { listExerciseOptions } from "@/lib/exercises";
import { UploadForm } from "./upload-form";

export const metadata: Metadata = { title: "Enviar vídeo" };

export default function UploadPage({ searchParams }: PageProps<"/upload">) {
  return (
    <>
      <h1 className="text-2xl font-semibold">Enviar vídeo</h1>
      <p className="mt-1 text-sm text-muted">
        Escolha o exercício e o arquivo. Cada envio vira uma nova versão, pendente de revisão.
      </p>
      <Suspense fallback={<div className="mt-6 h-80 animate-pulse rounded-xl bg-surface-muted" />}>
        <UploadLoader searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function UploadLoader({ searchParams }: { searchParams: PageProps<"/upload">["searchParams"] }) {
  const [params, options] = await Promise.all([searchParams, listExerciseOptions()]);
  const preselected = typeof params.exercicio === "string" ? params.exercicio : null;
  return <UploadForm options={options} initialSlug={preselected} />;
}
