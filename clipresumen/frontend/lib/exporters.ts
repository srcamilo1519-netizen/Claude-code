import type { SummaryDetail } from "@/lib/types";

function slug(text: string): string {
  return (
    text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "")
      .slice(0, 60) || "resumen"
  );
}

export function buildMarkdown(detail: SummaryDetail): string {
  const s = detail.summary;
  const lines: string[] = [
    `# ${s.titulo}`,
    "",
    `**Video:** ${detail.youtube_url}`,
    "",
    "## Puntos clave",
    ...s.puntos_clave.map((p) => `- ${p}`),
    "",
    "## Resumen extendido",
    s.resumen_extendido,
    "",
  ];
  if (s.timestamps_relevantes.length > 0) {
    lines.push("## Timestamps relevantes");
    for (const t of s.timestamps_relevantes) {
      lines.push(`- ${t.timestamp} — ${t.description}`);
    }
    lines.push("");
  }
  lines.push("## Conclusión / CTA", s.conclusion_cta, "");
  return lines.join("\n");
}

export function downloadText(
  filename: string,
  content: string,
  type = "text/markdown;charset=utf-8",
) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadMarkdown(detail: SummaryDetail) {
  downloadText(`${slug(detail.summary.titulo)}.md`, buildMarkdown(detail));
}

export async function downloadPdf(detail: SummaryDetail) {
  // Loaded lazily so jsPDF stays out of the main bundle.
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const margin = 48;
  const width = doc.internal.pageSize.getWidth() - margin * 2;
  const pageHeight = doc.internal.pageSize.getHeight();
  let y = margin;

  const write = (text: string, size: number, bold = false) => {
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    for (const line of doc.splitTextToSize(text, width)) {
      if (y > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y);
      y += size * 1.4;
    }
    y += 8;
  };

  const s = detail.summary;
  write(s.titulo, 18, true);
  write(`Video: ${detail.youtube_url}`, 9);
  write("Puntos clave", 13, true);
  for (const p of s.puntos_clave) write(`•  ${p}`, 11);
  write("Resumen extendido", 13, true);
  write(s.resumen_extendido, 11);
  if (s.timestamps_relevantes.length > 0) {
    write("Timestamps relevantes", 13, true);
    for (const t of s.timestamps_relevantes) {
      write(`•  ${t.timestamp} — ${t.description}`, 11);
    }
  }
  write("Conclusión / CTA", 13, true);
  write(s.conclusion_cta, 11);

  doc.save(`${slug(s.titulo)}.pdf`);
}
