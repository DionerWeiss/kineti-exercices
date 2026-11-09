"use client";

import { useActionState } from "react";
import { setPassword } from "@/app/actions/auth";
import { AuthCard, Field, FormMessage, SubmitButton } from "@/components/auth-card";

export default function SetPasswordPage() {
  const [state, action, pending] = useActionState(setPassword, null);
  return (
    <AuthCard title="Criar senha" subtitle="Use pelo menos 8 caracteres.">
      <form action={action} className="space-y-4">
        <Field label="Nova senha" name="password" type="password" autoComplete="new-password" required minLength={8} autoFocus />
        <Field label="Repita a senha" name="confirm" type="password" autoComplete="new-password" required minLength={8} />
        <FormMessage error={state?.error} />
        <SubmitButton pending={pending}>Salvar e entrar</SubmitButton>
      </form>
    </AuthCard>
  );
}
