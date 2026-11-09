import { signOut } from "@/app/actions/auth";
import { requireUser } from "@/lib/auth";

export async function UserMenu() {
  const user = await requireUser();
  return (
    <form action={signOut} className="flex items-center gap-3 text-sm">
      <span className="hidden text-white/70 sm:inline">{user.email}</span>
      <button
        type="submit"
        className="rounded-md border border-white/20 px-3 py-1 text-white/90 hover:bg-white/10"
      >
        Sair
      </button>
    </form>
  );
}
