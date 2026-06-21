"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import Navbar from "@/components/Navbar";
import Spinner from "@/components/Spinner";
import SummaryView from "@/components/SummaryView";
import {
  buildMarkdown,
  downloadMarkdown,
  downloadPdf,
} from "@/lib/exporters";
import type { SummaryDetail } from "@/lib/types";
import { extractVideoId } from "@/lib/youtube";

export default function SummaryPage() {
  const params = useParams<{ id: string }>();
  const [detail, setDetail] = useState<SummaryDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const res = await fetch(`/api/summaries/${params.id}`, { cache: "no-store" });
      if (!active) return;
      if (!res.ok) {
        setStatus("error");
        return;
      }
      setDetail(await res.json());
      setStatus("ready");
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onCopy() {
    if (!detail) return;
    await navigator.clipboard.writeText(buildMarkdown(detail));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (status === "loading") {
    return (
      <>
        <Navbar />
        <div className="flex min-h-[60vh] items-center justify-center gap-3 text-white/60">
          <Spinner /> Cargando resumen…
        </div>
      </>
    );
  }

  if (status === "error" || !detail) {
    return (
      <>
        <Navbar />
        <div className="mx-auto max-w-3xl px-4 py-24 text-center text-white/60">
          <p>No encontramos este resumen.</p>
          <Link href="/dashboard" className="mt-4 inline-block text-accent hover:underline">
            Volver al dashboard
          </Link>
        </div>
      </>
    );
  }

  const videoId = extractVideoId(detail.youtube_url);

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-8">
        {videoId && (
          <div className="mb-8 aspect-video w-full overflow-hidden rounded-2xl border border-white/10">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${videoId}`}
              title={detail.video_title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        )}

        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={onCopy}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm transition hover:bg-white/5"
          >
            {copied ? "¡Copiado!" : "Copiar resumen"}
          </button>
          <button
            onClick={() => downloadMarkdown(detail)}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm transition hover:bg-white/5"
          >
            Descargar Markdown
          </button>
          <button
            onClick={() => downloadPdf(detail)}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm transition hover:bg-white/5"
          >
            Descargar PDF
          </button>
        </div>

        <SummaryView summary={detail.summary} />
      </main>
    </>
  );
}
