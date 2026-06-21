/**
 * Resolve the backend base URL for server-side calls (Route Handlers).
 *
 * Inside Docker the frontend container reaches the backend at the service name
 * (`http://backend:8000`), so we prefer BACKEND_URL on the server and fall back
 * to the browser-facing NEXT_PUBLIC_API_URL.
 */
export function backendUrl(): string {
  return (
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  );
}
