"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import Navbar from "@/components/Navbar";
import Spinner from "@/components/Spinner";
import { useAuth } from "@/context/AuthContext";

type PaidPlan = "pro" | "business";

interface Plan {
  id: "free" | PaidPlan;
  name: string;
  price: string;
  cadence: string;
  features: string[];
  highlighted?: boolean;
}

const PLANS: Plan[] = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    cadence: "para empezar",
    features: ["5 resúmenes / mes", "Sin tarjeta", "Exportar a Markdown y PDF"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$9",
    cadence: "/ mes",
    features: ["100 resúmenes / mes", "Historial completo", "Soporte prioritario"],
    highlighted: true,
  },
  {
    id: "business",
    name: "Business",
    price: "$29",
    cadence: "/ mes",
    features: ["Resúmenes ilimitados", "Acceso a la API", "Soporte dedicado"],
  },
];

export default function PricingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loadingPlan, setLoadingPlan] = useState<PaidPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function subscribe(plan: PaidPlan) {
    setError(null);
    if (!user) {
      router.push("/login");
      return;
    }
    setLoadingPlan(plan);
    try {
      const res = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (res.status === 503) {
        setError("Los pagos aún no están configurados en este entorno.");
        return;
      }
      if (!res.ok) {
        throw new Error(data.detail ?? "No se pudo iniciar el pago.");
      }
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setLoadingPlan(null);
    }
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-12">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Planes
          </h1>
          <p className="mt-3 text-white/60">
            Empieza gratis y mejora cuando lo necesites.
          </p>
        </div>

        {error && (
          <p className="mx-auto mt-6 max-w-md text-center text-sm text-red-400">
            {error}
          </p>
        )}

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {PLANS.map((plan) => {
            const isCurrent = user?.plan === plan.id;
            return (
              <div
                key={plan.id}
                className={`flex flex-col rounded-2xl border p-6 ${
                  plan.highlighted
                    ? "border-accent bg-accent/10"
                    : "border-white/10 bg-white/5"
                }`}
              >
                <h2 className="text-lg font-semibold">{plan.name}</h2>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-sm text-white/50">{plan.cadence}</span>
                </div>

                <ul className="mt-6 flex-1 space-y-2 text-sm text-white/80">
                  {plan.features.map((f) => (
                    <li key={f} className="flex gap-2">
                      <span className="text-accent">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>

                <div className="mt-6">
                  {isCurrent ? (
                    <span className="block rounded-lg border border-white/10 px-4 py-2 text-center text-sm text-white/50">
                      Tu plan actual
                    </span>
                  ) : plan.id === "free" ? (
                    <Link
                      href={user ? "/dashboard" : "/register"}
                      className="block rounded-lg border border-white/10 px-4 py-2 text-center text-sm transition hover:bg-white/5"
                    >
                      {user ? "Ir al dashboard" : "Empezar gratis"}
                    </Link>
                  ) : (
                    <button
                      onClick={() => subscribe(plan.id as PaidPlan)}
                      disabled={loadingPlan !== null}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium transition hover:bg-accent-hover disabled:opacity-60"
                    >
                      {loadingPlan === plan.id && <Spinner />}
                      Suscribirse
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </>
  );
}
