import { listOrders } from "@/lib/api";

export async function GET() {
  return Response.json(listOrders());
}
