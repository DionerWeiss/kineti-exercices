"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";

type Props = { href: string; children: React.ReactNode };

const base = "rounded-md px-3 py-1.5 transition-colors";
const idle = "text-white/70 hover:bg-white/10 hover:text-white";
const current = "bg-white/15 text-white";

export function NavLink(props: Props) {
  // O caminho só existe em runtime; o fallback entra no shell estático sem destaque.
  return (
    <Suspense
      fallback={
        <Link href={props.href} className={`${base} ${idle}`}>
          {props.children}
        </Link>
      }
    >
      <ActiveLink {...props} />
    </Suspense>
  );
}

function ActiveLink({ href, children }: Props) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`${base} ${active ? current : idle}`}
    >
      {children}
    </Link>
  );
}
