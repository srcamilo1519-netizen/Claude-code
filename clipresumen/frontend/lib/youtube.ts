/** Extract the 11-char YouTube video id from common URL shapes. */
export function extractVideoId(url: string): string | null {
  const match = url.match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:[^&]*&)*v=|shorts\/|embed\/|v\/))([0-9A-Za-z_-]{11})/,
  );
  return match ? match[1] : null;
}

/** Format a duration in seconds as H:MM:SS or M:SS. */
export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
