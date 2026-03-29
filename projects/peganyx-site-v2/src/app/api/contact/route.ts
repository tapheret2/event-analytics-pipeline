import { NextRequest, NextResponse } from "next/server";

import { buildAcceptedContactPayload, buildErrorPayload, validateContactPayload } from "@/lib/api";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const normalized = validateContactPayload(body);

    console.info("[peganyx-contact] submission received", {
      ...normalized,
      messageLength: normalized.message.length,
    });

    const submissionId = `cnt_${Date.now().toString(36)}`;
    return NextResponse.json(buildAcceptedContactPayload(submissionId), { status: 201 });
  } catch (error) {
    const status = typeof error === "object" && error && "status" in error && typeof error.status === "number" ? error.status : 500;
    const code = typeof error === "object" && error && "code" in error && typeof error.code === "string" ? error.code : "INTERNAL_SERVER_ERROR";
    const message = error instanceof Error ? error.message : "Unexpected server failure";
    const details = typeof error === "object" && error && "details" in error ? error.details : undefined;

    return NextResponse.json(buildErrorPayload(code, message, details), { status });
  }
}
