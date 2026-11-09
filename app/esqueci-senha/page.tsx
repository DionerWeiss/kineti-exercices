"use client";

import Link from "next/link";
import { useActionState } from "react";
import { requestPasswordReset } from "@/app/actions/auth";
import { AuthCard, Field, FormMessage, SubmitButton } from "@/components/auth-card";

export default function ForgotPasswordPage() {
  const [state, action, pending] = useActionState(requestPasswordReset, null);
  return (
    <AuthCard title="Recuperar senha" subtitle="Enviamos um link para você criar uma senha nova.">
      <form action={action} className="space-y-4">
        <Field label="E-mail" name="email" type="email" autoComplete="email" required autoFocus />
        <FormMessage error={state?.error} message={state?.message} />
        <SubmitButton pending={pending}>Enviar link</SubmitButton>
        <p className="text-center text-sm">
          <Link href="/login" className="text-brand hover:underline">
            Voltar para o login
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
