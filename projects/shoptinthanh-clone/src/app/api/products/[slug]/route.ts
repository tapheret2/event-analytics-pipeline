import { apiError, getProductBySlug } from "@/lib/api";

export async function GET(_: Request, { params }: RouteContext<"/api/products/[slug]">) {
  const { slug } = await params;
  const product = getProductBySlug(slug);

  if (!product) {
    return apiError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.", [`slug=${slug}`]);
  }

  return Response.json({ product });
}
