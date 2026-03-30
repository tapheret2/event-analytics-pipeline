import { listOrders } from "@/lib/api";
import { PRODUCTS, STORE_INFO } from "@/lib/store-data";

export async function GET() {
  return Response.json({
    ok: true,
    service: "shoptinthanh-clone",
    timestamp: new Date().toISOString(),
    catalog: {
      products: PRODUCTS.length,
      orders: listOrders().total,
    },
    store: {
      city: STORE_INFO.city,
      province: STORE_INFO.province,
      hotline: STORE_INFO.hotline,
    },
  });
}
