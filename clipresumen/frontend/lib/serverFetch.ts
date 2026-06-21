import { cookies } from "next/headers";

import { backendUrl } from "@/lib/api";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  setAuthCookies,
} from "@/lib/authCookies";

/**
 * Call the backend with the user's access token (from the httpOnly cookie),
 * transparently refreshing it once on 401. Used by the data Route Handlers so
 * the browser never handles the JWT directly.
 */
export async function authedBackendFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const store = cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  const refresh = store.get(REFRESH_COOKIE)?.value;

  const call = (token?: string) =>
    fetch(`${backendUrl()}${path}`, {
      ...init,
      headers: {
        ...(init.headers ?? {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    });

  let res = await call(access);

  if (res.status === 401 && refresh) {
    const refreshed = await fetch(`${backendUrl()}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: "no-store",
    });
    if (refreshed.ok) {
      const tokens = await refreshed.json();
      setAuthCookies(tokens.access_token, tokens.refresh_token);
      res = await call(tokens.access_token);
    }
  }

  return res;
}
