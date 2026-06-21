import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClipResumen — Resúmenes de YouTube con IA",
  description:
    "Pega la URL de un video de YouTube y obtén un resumen estructurado en segundos.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
