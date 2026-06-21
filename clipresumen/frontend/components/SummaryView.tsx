import type { VideoSummary } from "@/lib/types";

export default function SummaryView({ summary }: { summary: VideoSummary }) {
  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold leading-tight sm:text-3xl">
          {summary.titulo}
        </h1>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-accent">
          Puntos clave
        </h2>
        <ul className="space-y-2">
          {summary.puntos_clave.map((point, i) => (
            <li key={i} className="flex gap-3 text-white/85">
              <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-accent" />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-accent">
          Resumen extendido
        </h2>
        <div className="space-y-4 text-white/80">
          {summary.resumen_extendido
            .split(/\n{2,}/)
            .filter(Boolean)
            .map((para, i) => (
              <p key={i}>{para}</p>
            ))}
        </div>
      </section>

      {summary.timestamps_relevantes.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-accent">
            Timestamps relevantes
          </h2>
          <ul className="space-y-2">
            {summary.timestamps_relevantes.map((t, i) => (
              <li key={i} className="flex gap-3 text-white/85">
                <span className="font-mono text-accent">{t.timestamp}</span>
                <span>{t.description}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-accent">
          Conclusión / CTA
        </h2>
        <p className="text-white/80">{summary.conclusion_cta}</p>
      </section>
    </div>
  );
}
