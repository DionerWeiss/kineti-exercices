"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useActionState } from "react";
import { signIn } from "@/app/actions/auth";
import { Field, FormMessage, SubmitButton } from "@/components/auth-card";

export function LoginForm() {
  const params = useSearchParams();
  const [state, action, pending] = useActionState(signIn, null);
  const linkError =
    params.get("erro") === "link" ? "O link expirou ou já foi usado. Peça um novo." : undefined;

  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="next" value={params.get("next") ?? ""} />
      <Field label="E-mail" name="email" type="email" autoComplete="email" required autoFocus />
      <Field label="Senha" name="password" type="password" autoComplete="current-password" required />
      <FormMessage error={state?.error ?? linkError} />
      <SubmitButton pending={pending}>Entrar</SubmitButton>
      <p className="text-center text-sm">
        <Link href="/esqueci-senha" className="text-brand hover:underline">
          Esqueci a senha
        </Link>
      </p>
    </form>
  );
}
