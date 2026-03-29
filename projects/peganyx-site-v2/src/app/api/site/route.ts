import { NextResponse } from "next/server";

import { buildSitePayload } from "@/lib/api";

export async function GET() {
  return NextResponse.json(buildSitePayload());
}
