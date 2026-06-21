"use client";

import Link from "next/link";

import { useAuth } from "@/context/AuthContext";

export default function Home() {
  const { user, loading, logout } = useAuth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <span className="mb-4 rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-widest text-white/50">
        Fase 4 · Auth
      </span>
      <h1 className="text-5xl font-bold tracking-tight">
        Clip<span className="text-accent">Resumen</span>
      </h1>
      <p className="mt-4 max-w-md text-balance text-white/60">
        Resúmenes de videos de YouTube con IA.
      </p>

      <div className="mt-8 flex items-center gap-3 text-sm">
        {loading ? (
          <span className="text-white/40">Cargando sesión…</span>
        ) : user ? (
          <>
            <span className="text-white/60">
              {user.email} · {user.credits_remaining} créditos
            </span>
            <button
              onClick={() => logout()}
              className="rounded-lg border border-white/10 px-4 py-2 transition hover:bg-white/5"
            >
              Cerrar sesión
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="rounded-lg border border-white/10 px-4 py-2 transition hover:bg-white/5"
            >
              Iniciar sesión
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-accent px-4 py-2 font-medium transition hover:bg-accent-hover"
            >
              Crear cuenta
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
