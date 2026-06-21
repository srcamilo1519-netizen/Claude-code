"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import Navbar from "@/components/Navbar";
import Spinner from "@/components/Spinner";
import { useAuth } from "@/context/AuthContext";

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsCredits, setNeedsCredits] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNeedsCredits(false);

    if (!user) {
      // Preview is open to everyone, but processing requires an account.
      router.push("/login");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (res.status === 402) {
        setNeedsCredits(true);
        return;
      }
      if (!res.ok) {
        throw new Error(data.detail ?? "No se pudo generar el resumen.");
      }
      router.push(`/summary/${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto flex max-w-3xl flex-col items-center px-4 pt-20 text-center sm:pt-28">
        <span className="mb-4 rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-widest text-white/50">
          Resúmenes de YouTube con IA
        </span>
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          Resume cualquier video en segundos
        </h1>
        <p className="mt-5 max-w-xl text-balance text-white/60">
          Pega el enlace de un video de YouTube y obtén un resumen estructurado:
          puntos clave, resumen extendido, momentos importantes y conclusión.
        </p>

        <form onSubmit={onSubmit} className="mt-10 w-full max-w-2xl">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=…"
              className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-left outline-none focus:border-accent"
            />
            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-xl bg-accent px-6 py-3 font-medium text-white transition hover:bg-accent-hover disabled:opacity-60"
            >
              {loading && <Spinner />}
              {loading ? "Resumiendo…" : "Resumir"}
            </button>
          </div>

          {!user && (
            <p className="mt-3 text-sm text-white/40">
              Necesitas una cuenta para procesar.{" "}
              <Link href="/register" className="text-accent hover:underline">
                Crear cuenta
              </Link>
            </p>
          )}
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          {needsCredits && (
            <p className="mt-3 text-sm text-amber-400">
              Te quedaste sin créditos.{" "}
              <Link href="/dashboard" className="underline">
                Revisa tu plan
              </Link>
              .
            </p>
          )}
        </form>
      </main>
    </>
  );
}
