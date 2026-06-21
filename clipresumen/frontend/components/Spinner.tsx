export default function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white ${className}`}
      role="status"
      aria-label="Cargando"
    />
  );
}
