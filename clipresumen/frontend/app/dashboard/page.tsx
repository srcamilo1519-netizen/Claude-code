"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Navbar from "@/components/Navbar";
import Spinner from "@/components/Spinner";
import { useAuth } from "@/context/AuthContext";
import type { SummaryListItem } from "@/lib/types";
import { formatDuration } from "@/lib/youtube";

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<SummaryListItem[] | null>(null);

  // Redirect unauthenticated users once the session has loaded.
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const res = await fetch("/api/summaries", { cache: "no-store" });
      setItems(res.ok ? await res.json() : []);
    })();
  }, [user]);

  async function openPortal() {
    const res = await fetch("/api/billing/portal", { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.url) {
      window.location.href = data.url;
    }
  }

  if (authLoading || !user) {
    return (
      <>
        <Navbar />
        <div className="flex min-h-[60vh] items-center justify-center text-white/60">
          <Spinner />
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/5 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Tu dashboard</h1>
            <p className="mt-1 text-white/60">{user.email}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-3xl font-bold text-accent">
                {user.credits_remaining}
              </div>
              <div className="text-xs uppercase tracking-widest text-white/40">
                créditos · plan {user.plan}
              </div>
            </div>
            {user.plan === "free" ? (
              <Link
                href="/pricing"
                className="rounded-lg bg-accent px-4 py-2 font-medium transition hover:bg-accent-hover"
              >
                Mejorar plan
              </Link>
            ) : (
              <button
                onClick={openPortal}
                className="rounded-lg border border-white/10 px-4 py-2 font-medium transition hover:bg-white/5"
              >
                Gestionar suscripción
              </button>
            )}
          </div>
        </div>

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Historial</h2>
          <Link href="/" className="text-sm text-accent hover:underline">
            + Nuevo resumen
          </Link>
        </div>

        {items === null ? (
          <div className="flex justify-center py-16 text-white/60">
            <Spinner />
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 py-16 text-center text-white/50">
            Aún no has generado resúmenes.{" "}
            <Link href="/" className="text-accent hover:underline">
              Crea el primero
            </Link>
            .
          </div>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/summary/${item.id}`}
                  className="block h-full rounded-xl border border-white/10 bg-white/5 p-4 transition hover:border-accent/50 hover:bg-white/10"
                >
                  <h3 className="line-clamp-2 font-medium">{item.video_title}</h3>
                  <p className="mt-2 text-xs text-white/40">
                    {formatDuration(item.video_duration)} ·{" "}
                    {new Date(item.created_at).toLocaleDateString("es")}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
