import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendUrl } from "@/lib/api";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  setAuthCookies,
} from "@/lib/authCookies";

async function fetchProfile(token: string) {
  return fetch(`${backendUrl()}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}

export async function GET() {
  const store = cookies();
  let accessToken = store.get(ACCESS_COOKIE)?.value;
  const refreshToken = store.get(REFRESH_COOKIE)?.value;

  if (!accessToken && !refreshToken) {
    return NextResponse.json({ user: null });
  }

  let res = accessToken ? await fetchProfile(accessToken) : undefined;

  // Access token missing/expired — try to rotate it with the refresh token.
  if ((!res || res.status === 401) && refreshToken) {
    const refreshed = await fetch(`${backendUrl()}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (refreshed.ok) {
      const tokens = await refreshed.json();
      accessToken = tokens.access_token;
      setAuthCookies(tokens.access_token, tokens.refresh_token);
      res = await fetchProfile(accessToken as string);
    }
  }

  if (!res || !res.ok) {
    return NextResponse.json({ user: null });
  }
  return NextResponse.json({ user: await res.json() });
}
