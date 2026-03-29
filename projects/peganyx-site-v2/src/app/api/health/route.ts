import { NextResponse } from "next/server";

import { buildMeta } from "@/lib/api";

export async function GET() {
  return NextResponse.json({ status: "ok", meta: buildMeta() });
}
