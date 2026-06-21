import { NextResponse } from "next/server";

import { authedBackendFetch } from "@/lib/serverFetch";

export async function GET() {
  const res = await authedBackendFetch("/api/summaries");
  const data = await res.json().catch(() => []);
  return NextResponse.json(data, { status: res.status });
}
