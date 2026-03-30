"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BLOG_POSTS, CATEGORIES, PRODUCTS, STORE_INFO, STORY_PARAGRAPHS, TRUST_BADGES, formatCurrency, getDepartment, getProduct, getRelatedProducts, type Product } from "@/lib/store-data";
import type { OrderRecord } from "@/lib/api";

export type CartItem = { slug: string; variant: string; size: string; quantity: number };
const CART_KEY = "shoptinthanh-cart";

function readJsonFromStorage<T>(key: string): T | null {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(key);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function useCart() {
  const [items, setItems] = useState<CartItem[]>(() => readJsonFromStorage<CartItem[]>(CART_KEY) ?? []);

  useEffect(() => {
    window.localStorage.setItem(CART_KEY, JSON.stringify(items));
  }, [items]);

  return { items, setItems };
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { items } = useCart();
  const count = items.reduce((sum, item) => sum + item.quantity, 0);
  return (
    <>
      <div className="border-b border-[#eadfd6] bg-[#2b1d17] text-white">
        <div className="container-shell flex flex-wrap gap-2 py-3 text-xs font-semibold sm:justify-between">
          <div className="flex flex-wrap gap-2">{TRUST_BADGES.map((badge) => <span key={badge} className="rounded-full bg-white/10 px-3 py-1">{badge}</span>)}</div>
          <span>{STORE_INFO.address}</span>
        </div>
      </div>
      <header className="sticky top-0 z-20 border-b border-[#eadfd6] bg-[rgba(255,250,246,.95)] backdrop-blur">
        <div className="container-shell flex items-center justify-between gap-4 py-4">
          <Link href="/" className="text-2xl font-black tracking-tight text-[#2b1d17]">Shop Tín Thành</Link>
          <nav className="hidden gap-5 text-sm font-semibold lg:flex">
            <Link href="/danh-muc/nu">Thời Trang Nữ</Link>
            <Link href="/danh-muc/nam">Thời Trang Nam</Link>
            <Link href="/danh-muc/khac">Khác</Link>
            <Link href="/cau-chuyen">Câu chuyện</Link>
            <Link href="/blog">Blog</Link>
            <Link href="/ho-tro/doi-tra">Chính sách</Link>
          </nav>
          <div className="flex items-center gap-3 text-sm font-semibold">
            <a href={STORE_INFO.zaloLink} target="_blank" rel="noreferrer" className="hidden rounded-full border border-[#eadfd6] px-4 py-2 sm:inline-flex">Đặt qua Zalo</a>
            <Link href="/gio-hang" className="rounded-full bg-[#7c3f00] px-4 py-2 text-white">Giỏ hàng ({count})</Link>
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="mt-16 border-t border-[#eadfd6] bg-[#2b1d17] text-white">
        <div className="container-shell grid gap-8 py-12 md:grid-cols-4">
          <div>
            <h3 className="text-lg font-bold">Dịch vụ khách hàng</h3>
            <ul className="mt-3 space-y-2 text-sm text-white/80">
              <li>{STORE_INFO.address}</li>
              <li>Hotline: {STORE_INFO.hotline}</li>
              <li>{STORE_INFO.email}</li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-bold">Về Tín Thành</h3>
            <ul className="mt-3 space-y-2 text-sm text-white/80">
              <li><Link href="/cau-chuyen">Câu chuyện của Tín Thành</Link></li>
              <li><Link href="/ho-tro/tuyen-dung">Tuyển dụng</Link></li>
              <li><Link href="/blog">Blog</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-bold">Chính sách đổi và hỗ trợ</h3>
            <ul className="mt-3 space-y-2 text-sm text-white/80">
              <li><Link href="/ho-tro/doi-tra">Đổi trả</Link></li>
              <li><Link href="/ho-tro/tu-van-size">Tư vấn size</Link></li>
              <li><Link href="/ho-tro/thanh-toan">Thanh toán</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-bold">Kết nối</h3>
            <div className="mt-3 flex flex-col gap-2 text-sm text-white/80">
              <a href={STORE_INFO.facebookLink} target="_blank" rel="noreferrer">Facebook</a>
              <a href={STORE_INFO.zaloLink} target="_blank" rel="noreferrer">Zalo</a>
              <a href={STORE_INFO.phoneLink}>Gọi ngay</a>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}

export function HomePage() {
  const featured = PRODUCTS.filter((item) => item.featured).slice(0, 6);
  const fresh = PRODUCTS.filter((item) => item.isNew).slice(0, 4);
  return (
    <AppShell>
      <section className="container-shell py-8">
        <div className="hero-grid">
          <div className="card-surface overflow-hidden p-8">
            <span className="eyebrow">Storefront clone nâng cấp</span>
            <h1 className="mt-5 text-4xl font-black leading-tight text-[#231815] sm:text-6xl">Thời trang nam nữ Cao Lãnh, rõ danh mục, dễ mua, hỗ trợ nhanh.</h1>
            <p className="mt-5 max-w-2xl text-lg text-muted">Giữ đúng tinh thần Shop Tín Thành: nhóm danh mục quen thuộc, trust signals địa phương, hotline/Zalo nổi bật và luồng mua hàng thực dụng hơn.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/danh-muc/nu" className="rounded-full bg-[#7c3f00] px-6 py-3 font-semibold text-white">Mua nữ</Link>
              <Link href="/danh-muc/nam" className="rounded-full border border-[#eadfd6] px-6 py-3 font-semibold">Mua nam</Link>
              <Link href="/checkout" className="rounded-full border border-[#eadfd6] px-6 py-3 font-semibold">Xem checkout demo</Link>
            </div>
          </div>
          <div className="grid gap-4">
            <div className="card-surface bg-[#2b1d17] p-6 text-white">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/70">Uy tín địa phương</p>
              <h2 className="mt-2 text-2xl font-bold">Cửa hàng tại {STORE_INFO.city}, {STORE_INFO.province}</h2>
              <p className="mt-3 text-white/80">Giao COD, đổi hàng 7 ngày, chốt đơn nhanh qua Zalo hoặc hotline khi khách cần tư vấn size.</p>
            </div>
            <div className="card-surface p-6">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#8b5a2b]">Danh mục chính</p>
              <div className="mt-4 grid gap-3">{CATEGORIES.map((group) => <Link key={group.slug} href={`/danh-muc/${group.slug}`} className="rounded-2xl border border-[#eadfd6] px-4 py-4 font-semibold hover:bg-[#fff8f1]">{group.label}</Link>)}</div>
            </div>
          </div>
        </div>
      </section>
      <section className="container-shell py-8">
        <div className="mb-5 flex items-end justify-between gap-4"><div><span className="eyebrow">Danh mục nổi bật</span><h2 className="section-title mt-3">Nhóm sản phẩm theo đúng tinh thần gốc</h2></div></div>
        <div className="grid gap-4 md:grid-cols-3">{CATEGORIES.map((group) => <div key={group.slug} className="card-surface p-6"><h3 className="text-xl font-bold">{group.label}</h3><p className="mt-2 text-sm text-muted">{group.description}</p><div className="mt-4 flex flex-wrap gap-2">{group.subcategories.slice(0,6).map((sub) => <span key={sub.slug} className="rounded-full bg-[#fff8f1] px-3 py-2 text-sm">{sub.label}</span>)}</div><Link href={`/danh-muc/${group.slug}`} className="mt-5 inline-flex font-semibold text-[#7c3f00]">Xem danh mục →</Link></div>)}</div>
      </section>
      <ProductSection title="Bán chạy tại cửa hàng" products={featured} />
      <ProductSection title="Mới lên kệ" products={fresh} />
      <section className="container-shell py-8">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ["Miễn phí vận chuyển", "Đơn từ 300.000đ trong khu vực ưu tiên freeship."],
            ["Đổi hàng 7 ngày", "Hỗ trợ đổi size nhanh với tình trạng sản phẩm còn mới."],
            ["Đặt nhanh qua Zalo", "Khách quen có thể chụp mã SKU và chốt đơn trực tiếp."],
          ].map(([title, desc]) => <div key={title} className="card-surface p-6"><h3 className="text-lg font-bold">{title}</h3><p className="mt-2 text-sm text-muted">{desc}</p></div>)}
        </div>
      </section>
    </AppShell>
  );
}

function ProductSection({ title, products }: { title: string; products: Product[] }) {
  return <section className="container-shell py-8"><div className="mb-5 flex items-end justify-between gap-4"><div><span className="eyebrow">Merchandising</span><h2 className="section-title mt-3">{title}</h2></div><Link href="/san-pham" className="font-semibold text-[#7c3f00]">Xem tất cả</Link></div><ProductGrid products={products} /></section>;
}

export function ProductGrid({ products }: { products: Product[] }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{products.map((product) => <ProductCard key={product.slug} product={product} />)}</div>;
}

export function ProductCard({ product }: { product: Product }) {
  return <Link href={`/san-pham/${product.slug}`} className="card-surface overflow-hidden p-4 transition hover:-translate-y-1"><div className="flex h-56 items-end rounded-3xl p-4" style={{ background: product.images[0] as string }}><div className="rounded-full bg-white/90 px-3 py-1 text-xs font-bold">{product.subcategory}</div></div><div className="mt-4"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#8b5a2b]"><span>{product.department}</span>{product.isNew && <span className="rounded-full bg-[#7c3f00] px-2 py-1 text-white">Mới</span>}</div><h3 className="mt-2 text-lg font-bold text-[#231815]">{product.name}</h3><div className="mt-3 flex items-center gap-3"><span className="text-lg font-black text-[#7c3f00]">{formatCurrency(product.price)}</span>{product.compareAtPrice && <span className="text-sm text-muted line-through">{formatCurrency(product.compareAtPrice)}</span>}</div><div className="mt-3 flex items-center justify-between"><div className="flex -space-x-1">{product.colors.slice(0,4).map((color) => <span key={color.sku} className="product-swatch" style={{ background: color.code }} title={color.label} />)}</div><span className="text-sm text-muted">★ {product.rating} ({product.reviewCount})</span></div></div></Link>;
}

export function ListingPage({ departmentSlug, subcategory }: { departmentSlug?: string; subcategory?: string }) {
  const department = departmentSlug ? getDepartment(departmentSlug) : undefined;
  const products = PRODUCTS.filter((product) => (!departmentSlug || product.department === departmentSlug) && (!subcategory || product.subcategory === subcategory));
  return <AppShell><section className="container-shell py-8"><div className="card-surface p-6"><p className="text-sm text-muted">Trang chủ / Danh mục {department ? ` / ${department.label}` : " / Tất cả sản phẩm"}{subcategory ? ` / ${subcategory}` : ""}</p><h1 className="mt-3 text-4xl font-black text-[#231815]">{department?.label ?? "Toàn bộ sản phẩm"}</h1><p className="mt-3 max-w-3xl text-muted">{department?.description ?? "Danh sách sản phẩm seeded theo tinh thần Shop Tín Thành, có lọc API và giao diện duyệt thực tế hơn bản gốc."}</p><div className="mt-6 grid gap-4 lg:grid-cols-[280px_1fr]"><aside className="card-surface p-5"><h2 className="font-bold">Bộ lọc nhanh</h2><div className="mt-4 space-y-4 text-sm">{department?.subcategories.map((sub) => <Link key={sub.slug} href={`/san-pham?department=${department.slug}&subcategory=${sub.slug}`} className="block rounded-2xl border border-[#eadfd6] px-4 py-3">{sub.label}</Link>) ?? <>{CATEGORIES.flatMap((group) => group.subcategories.slice(0, 8)).map((sub) => <span key={sub.slug} className="block rounded-2xl border border-[#eadfd6] px-4 py-3">{sub.label}</span>)}</>}</div></aside><div><div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-[#eadfd6] bg-white px-5 py-4"><p className="text-sm text-muted">{products.length} sản phẩm • API hỗ trợ department/category/subcategory/search/sort/color/size/minPrice/maxPrice</p><div className="flex gap-2 text-sm"><span className="rounded-full bg-[#fff8f1] px-3 py-2">Sort: giá tăng/giảm</span><span className="rounded-full bg-[#fff8f1] px-3 py-2">Search</span></div></div><ProductGrid products={products} /></div></div></div></section></AppShell>;
}

export function ProductDetailPage({ slug }: { slug: string }) {
  const product = getProduct(slug);
  const related = product ? getRelatedProducts(product) : [];
  const { setItems } = useCart();
  const [selectedColor, setSelectedColor] = useState(product?.colors[0]?.sku ?? "");
  const [selectedSize, setSelectedSize] = useState(product?.sizes[0] ?? "");
  const [quantity, setQuantity] = useState(1);
  if (!product) return <AppShell><section className="container-shell py-16"><div className="card-surface p-8"><h1 className="text-3xl font-bold">Không tìm thấy sản phẩm</h1></div></section></AppShell>;
  return <AppShell><section className="container-shell py-8"><div className="card-surface p-6"><p className="text-sm text-muted">Trang chủ / {getDepartment(product.department)?.label} / {product.name}</p><div className="mt-6 grid gap-8 lg:grid-cols-[1fr_0.95fr]"><div className="space-y-4"><div className="flex h-[480px] items-end rounded-[32px] p-6" style={{ background: product.images[0] as string }}><span className="rounded-full bg-white/90 px-4 py-2 text-sm font-semibold">SKU đang chọn: {selectedColor}</span></div><div className="grid grid-cols-3 gap-3">{product.images.map((image, index) => <div key={index} className="h-28 rounded-3xl" style={{ background: image as string }} />)}</div></div><div><span className="eyebrow">Sản phẩm chi tiết</span><h1 className="mt-4 text-4xl font-black text-[#231815]">{product.name}</h1><div className="mt-3 flex items-center gap-3"><span className="text-3xl font-black text-[#7c3f00]">{formatCurrency(product.price)}</span>{product.compareAtPrice && <span className="text-lg text-muted line-through">{formatCurrency(product.compareAtPrice)}</span>}</div><p className="mt-4 text-muted">{product.description}</p><div className="mt-6"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#8b5a2b]">Màu / mã SKU</p><div className="mt-3 flex flex-wrap gap-3">{product.colors.map((color) => <button key={color.sku} onClick={() => setSelectedColor(color.sku)} className={`rounded-2xl border px-4 py-3 text-left ${selectedColor === color.sku ? "border-[#7c3f00] bg-[#fff8f1]" : "border-[#eadfd6]"}`}><div className="flex items-center gap-3"><span className="product-swatch" style={{ background: color.code }} /><div><p className="font-semibold">{color.label}</p><p className="text-xs text-muted">{color.sku}</p></div></div></button>)}</div></div><div className="mt-6"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#8b5a2b]">Kích thước</p><div className="mt-3 flex flex-wrap gap-2">{product.sizes.map((size) => <button key={size} onClick={() => setSelectedSize(size)} className={`rounded-full px-4 py-2 font-semibold ${selectedSize === size ? "bg-[#2b1d17] text-white" : "border border-[#eadfd6]"}`}>{size}</button>)}</div></div><div className="mt-6 flex items-center gap-3"><div className="flex items-center rounded-full border border-[#eadfd6] bg-white px-3 py-2"><button onClick={() => setQuantity((v) => Math.max(1, v - 1))} className="px-3">-</button><span className="w-8 text-center font-semibold">{quantity}</span><button onClick={() => setQuantity((v) => v + 1)} className="px-3">+</button></div><button onClick={() => setItems((prev) => [...prev, { slug: product.slug, variant: selectedColor, size: selectedSize, quantity }])} className="rounded-full bg-[#7c3f00] px-6 py-3 font-semibold text-white">Thêm vào giỏ</button><a href={STORE_INFO.zaloLink} target="_blank" rel="noreferrer" className="rounded-full border border-[#eadfd6] px-6 py-3 font-semibold">Đặt qua Zalo</a></div><div className="mt-6 grid gap-3 sm:grid-cols-3">{["Miễn phí vận chuyển đơn từ 300K", "Đổi hàng trong 7 ngày", "COD toàn quốc"].map((item) => <div key={item} className="rounded-3xl border border-[#eadfd6] bg-white px-4 py-4 text-sm font-semibold">{item}</div>)}</div></div></div></div></section><section className="container-shell py-4"><div className="card-surface p-6"><h2 className="text-2xl font-bold">Mô tả sản phẩm</h2><p className="mt-4 leading-7 text-muted">{product.description} Shop ưu tiên mô tả rõ chất liệu, mục đích sử dụng, size dễ chọn và kênh liên hệ nhanh để khách địa phương hoặc khách ở tỉnh khác đều chốt đơn thuận tiện.</p></div></section><section className="container-shell py-8"><div className="mb-5"><span className="eyebrow">Liên quan</span><h2 className="section-title mt-3">Sản phẩm gợi ý</h2></div><ProductGrid products={related} /></section></AppShell>;
}

export function CartPage() {
  const { items, setItems } = useCart();
  const enriched = items.map((item) => ({ ...item, product: getProduct(item.slug) })).filter((item) => item.product);
  const subtotal = enriched.reduce((sum, item) => sum + item.quantity * item.product!.price, 0);
  const shipping = subtotal >= 300000 ? 0 : enriched.length ? 30000 : 0;
  return <AppShell><section className="container-shell py-8"><div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]"><div className="card-surface p-6"><h1 className="text-3xl font-black text-[#231815]">Giỏ hàng</h1><div className="mt-5 space-y-4">{enriched.length ? enriched.map((item, index) => <div key={`${item.slug}-${index}`} className="flex flex-col gap-4 rounded-3xl border border-[#eadfd6] p-4 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="text-lg font-bold">{item.product!.name}</h3><p className="text-sm text-muted">{item.variant} • Size {item.size}</p></div><div className="text-right"><p className="font-bold text-[#7c3f00]">{formatCurrency(item.product!.price * item.quantity)}</p><button onClick={() => setItems(items.filter((_, i) => i !== index))} className="mt-2 text-sm text-muted underline">Xóa</button></div></div>) : <p className="text-muted">Chưa có sản phẩm. Hãy thêm từ trang chi tiết.</p>}</div></div><div className="card-surface p-6"><h2 className="text-2xl font-bold">Tóm tắt đơn</h2><div className="mt-4 space-y-3 text-sm"><div className="flex justify-between"><span>Tạm tính</span><span>{formatCurrency(subtotal)}</span></div><div className="flex justify-between"><span>Vận chuyển</span><span>{formatCurrency(shipping)}</span></div><div className="flex justify-between border-t border-[#eadfd6] pt-3 text-lg font-bold"><span>Tổng cộng</span><span>{formatCurrency(subtotal + shipping)}</span></div></div><Link href="/checkout" className="mt-6 inline-flex rounded-full bg-[#7c3f00] px-6 py-3 font-semibold text-white">Tiến hành checkout</Link></div></div></section></AppShell>;
}

export function CheckoutPage() {
  const { items, setItems } = useCart();
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const enriched = items.map((item) => ({ ...item, product: getProduct(item.slug) })).filter((item) => item.product);
  const subtotal = enriched.reduce((sum, item) => sum + item.quantity * item.product!.price, 0);
  const shipping = subtotal >= 300000 ? 0 : 30000;
  async function submitOrder(formData: FormData) {
    setLoading(true);
    setStatus("");
    const payload = {
      customer: {
        firstName: formData.get("firstName"),
        lastName: formData.get("lastName"),
        email: formData.get("email"),
        phone: formData.get("phone"),
        address: formData.get("address"),
        city: formData.get("city"),
        postalCode: formData.get("postalCode")
      },
      paymentMethod: formData.get("paymentMethod"),
      shippingMethod: formData.get("shippingMethod"),
      items,
      notes: formData.get("notes")
    };
    const response = await fetch("/api/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error?.message || data.error || "Không thể tạo đơn hàng");
      setLoading(false);
      return;
    }
    window.localStorage.setItem("last-order", JSON.stringify(data.order));
    setItems([]);
    window.location.href = "/checkout/thanh-cong";
  }
  return <AppShell><section className="container-shell py-8"><div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]"><form action={submitOrder} className="card-surface p-6"><h1 className="text-3xl font-black text-[#231815]">Checkout demo</h1><p className="mt-2 text-sm text-muted">Luồng này dùng API mock nội bộ và xác nhận đơn hàng demo, không kết nối cổng thanh toán thật.</p><div className="mt-5 grid gap-4 sm:grid-cols-2">{["firstName", "lastName", "email", "phone", "address", "city", "postalCode"].map((field) => <input key={field} name={field} placeholder={field} required={field !== "postalCode" && field !== "email"} className="rounded-2xl border border-[#eadfd6] px-4 py-3" />)}</div><div className="mt-4 grid gap-4 sm:grid-cols-2"><select name="paymentMethod" className="rounded-2xl border border-[#eadfd6] px-4 py-3"><option value="cod">COD</option><option value="bank-transfer">Chuyển khoản demo</option></select><select name="shippingMethod" className="rounded-2xl border border-[#eadfd6] px-4 py-3"><option value="standard">Giao tiêu chuẩn</option><option value="express">Giao nhanh nội tỉnh</option></select></div><textarea name="notes" placeholder="Ghi chú giao hàng" className="mt-4 min-h-28 w-full rounded-2xl border border-[#eadfd6] px-4 py-3" />{status && <p className="mt-3 text-sm font-semibold text-red-600">{status}</p>}<button disabled={loading || !items.length} className="mt-5 rounded-full bg-[#7c3f00] px-6 py-3 font-semibold text-white disabled:opacity-50">{loading ? "Đang tạo đơn..." : "Xác nhận đơn demo"}</button></form><div className="card-surface p-6"><h2 className="text-2xl font-bold">Đơn hàng của bạn</h2><div className="mt-4 space-y-4">{enriched.map((item, index) => <div key={index} className="rounded-3xl border border-[#eadfd6] p-4"><div className="flex items-center justify-between gap-3"><div><h3 className="font-bold">{item.product!.name}</h3><p className="text-sm text-muted">{item.variant} • {item.size} • SL {item.quantity}</p></div><span className="font-bold text-[#7c3f00]">{formatCurrency(item.product!.price * item.quantity)}</span></div></div>)}</div><div className="mt-5 space-y-2 border-t border-[#eadfd6] pt-4 text-sm"><div className="flex justify-between"><span>Tạm tính</span><span>{formatCurrency(subtotal)}</span></div><div className="flex justify-between"><span>Vận chuyển</span><span>{formatCurrency(items.length ? shipping : 0)}</span></div><div className="flex justify-between text-lg font-bold"><span>Tổng</span><span>{formatCurrency(subtotal + (items.length ? shipping : 0))}</span></div></div></div></div></section></AppShell>;
}

export function SuccessPage() {
  const [order] = useState<OrderRecord | null>(() => readJsonFromStorage<OrderRecord>("last-order"));
  return <AppShell><section className="container-shell py-16"><div className="card-surface mx-auto max-w-3xl p-8 text-center"><span className="eyebrow">Đặt hàng thành công</span><h1 className="mt-4 text-4xl font-black text-[#231815]">Đơn demo đã được xác nhận</h1><p className="mt-4 text-muted">Storefront đã hoàn thiện luồng cart → checkout → success theo contract. Đây là trạng thái staging/mock, chưa có cổng thanh toán thật.</p>{order && <div className="mt-6 rounded-3xl border border-[#eadfd6] bg-white p-6 text-left"><p className="font-bold">Mã đơn: {order.id}</p><p className="text-sm text-muted">Tổng đơn: {formatCurrency(order.total)}</p><p className="text-sm text-muted">Trạng thái: {order.status}</p></div>}<div className="mt-6 flex justify-center gap-3"><Link href="/san-pham" className="rounded-full bg-[#7c3f00] px-6 py-3 font-semibold text-white">Tiếp tục mua sắm</Link><Link href="/" className="rounded-full border border-[#eadfd6] px-6 py-3 font-semibold">Về trang chủ</Link></div></div></section></AppShell>;
}

export function StoryPage() { return <AppShell><section className="container-shell py-8"><div className="card-surface p-8"><span className="eyebrow">Câu chuyện của Tín Thành</span><h1 className="mt-4 text-4xl font-black text-[#231815]">Một cửa hàng thời trang địa phương làm mọi thứ rõ ràng và vừa túi tiền.</h1><div className="mt-6 grid gap-5 lg:grid-cols-[1fr_0.7fr]"><div className="space-y-4 text-lg leading-8 text-muted">{STORY_PARAGRAPHS.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</div><div className="card-surface bg-[#2b1d17] p-6 text-white"><h2 className="text-2xl font-bold">Điều khách nhớ nhất</h2><ul className="mt-4 space-y-3 text-white/80"><li>• Danh mục đủ quen để không bị rối</li><li>• Có người tư vấn thật qua Zalo/hotline</li><li>• Giá niêm yết rõ, size dễ chọn</li><li>• Chính sách đổi hàng dễ hiểu</li></ul></div></div></div></section></AppShell>; }

export function BlogPage() { return <AppShell><section className="container-shell py-8"><div className="mb-6"><span className="eyebrow">Blog</span><h1 className="section-title mt-3">Mẹo phối đồ, tư vấn size và chăm sóc sản phẩm</h1></div><div className="grid gap-4 md:grid-cols-3">{BLOG_POSTS.map((post) => <article key={post.slug} className="card-surface p-6"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8b5a2b]">{post.category}</p><h2 className="mt-3 text-xl font-bold">{post.title}</h2><p className="mt-3 text-sm text-muted">{post.excerpt}</p><div className="mt-4 text-sm text-muted">{post.publishedAt} • {post.readTime}</div></article>)}</div></section></AppShell>; }

export function PolicyPage({ title, body }: { title: string; body: string[] }) { return <AppShell><section className="container-shell py-8"><div className="card-surface p-8"><span className="eyebrow">Hỗ trợ khách hàng</span><h1 className="mt-4 text-4xl font-black text-[#231815]">{title}</h1><div className="mt-6 space-y-4 text-lg leading-8 text-muted">{body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</div></div></section></AppShell>; }
