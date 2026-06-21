import { NextResponse } from "next/server";

import { authedBackendFetch } from "@/lib/serverFetch";

export async function POST(req: Request) {
  const body = await req.text();
  const res = await authedBackendFetch("/api/billing/create-checkout-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
