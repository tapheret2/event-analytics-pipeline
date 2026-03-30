import { getCategoriesPayload } from "@/lib/api";

export async function GET() {
  return Response.json(getCategoriesPayload());
}
