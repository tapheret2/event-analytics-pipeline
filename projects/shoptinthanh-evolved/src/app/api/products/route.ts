import { NextRequest } from "next/server";
import { listProducts } from "@/lib/api";

export async function GET(request: NextRequest) {
  const result = listProducts(request.nextUrl.searchParams);
  if (!result.ok) return result.response;
  return Response.json(result.body);
}
