import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthCard } from "@/components/auth-card";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Entrar" };

export default function LoginPage() {
  return (
    <AuthCard title="Entrar" subtitle="Acesso apenas para convidados.">
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthCard>
  );
}
