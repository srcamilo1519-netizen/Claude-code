"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  async function onLogout() {
    await logout();
    router.push("/");
  }

  return (
    <header className="sticky top-0 z-10 border-b border-white/10 bg-black/70 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight">
          Clip<span className="text-accent">Resumen</span>
        </Link>

        <div className="flex items-center gap-2 text-sm sm:gap-4">
          {loading ? null : user ? (
            <>
              <span className="hidden rounded-full bg-white/5 px-3 py-1 text-white/70 sm:inline">
                {user.credits_remaining} créditos
              </span>
              <Link href="/dashboard" className="text-white/80 hover:text-white">
                Dashboard
              </Link>
              <button
                onClick={onLogout}
                className="rounded-lg border border-white/10 px-3 py-1.5 transition hover:bg-white/5"
              >
                Salir
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-white/80 hover:text-white">
                Entrar
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-accent px-3 py-1.5 font-medium transition hover:bg-accent-hover"
              >
                Crear cuenta
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
