export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <span className="mb-4 rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-widest text-white/50">
        Fase 0 · Skeleton
      </span>
      <h1 className="text-5xl font-bold tracking-tight">
        Clip<span className="text-accent">Resumen</span>
      </h1>
      <p className="mt-4 max-w-md text-balance text-white/60">
        Resúmenes de videos de YouTube con IA. El esqueleto está en marcha — la
        interfaz funcional llega en la Fase 5.
      </p>
      <div className="mt-8 text-sm text-white/40">
        Backend API:{" "}
        <code className="rounded bg-white/5 px-2 py-1 text-accent">
          {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
        </code>
      </div>
    </main>
  );
}
