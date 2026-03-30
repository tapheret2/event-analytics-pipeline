import { NextRequest } from "next/server";
import { apiError, createOrder } from "@/lib/api";

export async function POST(request: NextRequest) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return apiError(400, "INVALID_JSON", "Body JSON không hợp lệ.");
  }

  const result = createOrder(body);
  if (!result.ok) {
    return result.response;
  }

  return Response.json(result.body, { status: 201 });
}
