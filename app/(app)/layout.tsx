import Link from "next/link";
import { Suspense } from "react";
import { NavLink } from "@/components/nav-link";
import { UserMenu } from "@/components/user-menu";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="sticky top-0 z-20 bg-ink text-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
          <Link href="/exercicios" className="flex items-baseline gap-2 font-semibold">
            Kineti
            <span className="text-sm font-normal text-white/60">revisão de vídeos</span>
          </Link>
          <nav className="flex gap-1 text-sm">
            <NavLink href="/exercicios">Exercícios</NavLink>
            <NavLink href="/upload">Enviar vídeo</NavLink>
          </nav>
          <div className="ml-auto">
            <Suspense fallback={<span className="text-sm text-white/40">…</span>}>
              <UserMenu />
            </Suspense>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
    </>
  );
}
