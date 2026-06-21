import { NextResponse } from "next/server";

import { backendUrl } from "@/lib/api";
import { setAuthCookies } from "@/lib/authCookies";

export async function POST(req: Request) {
  const body = await req.json();
  const res = await fetch(`${backendUrl()}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }
  setAuthCookies(data.access_token, data.refresh_token);
  return NextResponse.json({ ok: true });
}
