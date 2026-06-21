import { NextResponse } from "next/server";

import { authedBackendFetch } from "@/lib/serverFetch";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } },
) {
  const res = await authedBackendFetch(`/api/summaries/${params.id}`);
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
