import { getHealthPayload } from "@/lib/api";

export async function GET() {
  return Response.json(getHealthPayload());
}
