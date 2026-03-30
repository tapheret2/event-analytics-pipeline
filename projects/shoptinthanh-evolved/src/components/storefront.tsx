"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { BLOG_POSTS, CATEGORIES, PRODUCTS, STORE, formatCurrency, getDepartment, getProduct, type Product } from "@/lib/store-data";

type CartItem = { slug: string; variant: string; size: string; quantity: number };
const CART_KEY = "shoptinthanh-evolved-cart";
const banners = ["/ref/1.png", "/ref/2.png", "/ref/3.png", "/ref/4.png", "/ref/5.png"];

type StoredOrder = { id: string; status: string; total: number } | null;

function useCart() {
  const [items, setItems] = useState<CartItem[]>(() => {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem(CART_KEY);
    return raw ? (JSON.parse(raw) as CartItem[]) : [];
  });
  useEffect(() => { window.localStorage.setItem(CART_KEY, JSON.stringify(items)); }, [items]);
  return { items, setItems };
}

function Header() {
  const [open, setOpen] = useState(false);
  return <header className="sticky top-0 z-20 w-full bg-white shadow-md"><div className="container-shell"><div className="flex items-center justify-between gap-4 py-3"><button className="lg:hidden" onClick={() => setOpen((v) => !v)}>☰</button><Link href="/" className="shrink-0"><Image src="/ref/logo.png" alt="logo" width={200} height={80} /></Link><nav className="hidden lg:flex items-center text-[15px]">{CATEGORIES.map((group) => <div key={group.slug} className="group relative px-4 py-5"><Link href={`/danh-muc/${group.slug}`} className="flex items-center gap-2 capitalize">{group.label}<span>▾</span></Link><div className="absolute left-0 top-full hidden min-w-[760px] bg-white p-5 shadow-lg group-hover:block"><div className="grid grid-cols-4 gap-4">{group.subcategories.map((sub) => <Link key={sub.slug} href={`/tim-kiem?department=${group.slug}&subcategory=${sub.slug}`} className="hover:text-[#b45f06]">{sub.label}</Link>)}</div></div></div>)}<Link className="px-4" href="/cau-chuyen">Câu chuyện của Tín Thành</Link><Link className="px-4" href="/blog">Blog</Link></nav><div className="flex items-center gap-4"><Link href="/tim-kiem" aria-label="search">⌕</Link><Link href="/gio-hang">Giỏ hàng</Link></div></div>{open && <div className="space-y-3 border-t py-4 lg:hidden">{CATEGORIES.map((group) => <div key={group.slug}><Link href={`/danh-muc/${group.slug}`} className="block font-semibold">{group.label}</Link><div className="mt-2 grid gap-2 pl-3 text-sm">{group.subcategories.slice(0,6).map((s) => <Link key={s.slug} href={`/tim-kiem?department=${group.slug}&subcategory=${s.slug}`}>{s.label}</Link>)}</div></div>)}<Link href="/cau-chuyen">Câu chuyện</Link><Link href="/blog" className="block">Blog</Link></div>}</div></header>;
}

function Footer() {
  return <footer className="mt-16 bg-white pt-10 text-sm text-[#444]"><div className="container-shell grid gap-8 border-t pt-10 md:grid-cols-4"><div><Image src="/ref/logo-footer.png" alt="logo footer" width={180} height={80} /><p className="mt-3">{STORE.address}</p><p>Hotline: {STORE.hotline}</p><p>{STORE.email}</p></div><div><h3 className="font-bold">Về Tín Thành</h3><div className="mt-3 grid gap-2"><Link href="/cau-chuyen">Câu chuyện</Link><Link href="/ho-tro/tuyen-dung">Tuyển dụng</Link><Link href="/blog">Blog</Link></div></div><div><h3 className="font-bold">Chính sách đổi và hỗ trợ</h3><div className="mt-3 grid gap-2"><Link href="/ho-tro/doi-tra">Đổi trả</Link><Link href="/ho-tro/tu-van-size">Tư vấn size</Link><Link href="/ho-tro/thanh-toan">Thanh toán</Link></div></div><div><h3 className="font-bold">Kết nối</h3><div className="mt-3 grid gap-2"><a href={STORE.facebook}>Facebook</a><a href={STORE.zalo}>Zalo</a><a href={`tel:${STORE.hotline.replace(/\./g,"")}`}>Gọi ngay</a></div></div></div><div className="container-shell py-6 text-xs text-[#777]">© 2026 Shop Tín Thành evolved storefront.</div></footer>;
}

export function Shell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-white"><Header />{children}<Footer /></div>;
}

function ProductCard({ product }: { product: Product }) {
  return <Link href={`/san-pham/${product.slug}`} className="group block"><div className="overflow-hidden rounded-sm border border-[#eee] bg-white"><div className="relative aspect-[3/4] bg-[#fafafa]"><Image src={product.images[0]} alt={product.name} fill className="object-cover transition duration-300 group-hover:scale-[1.02]" /></div><div className="p-3"><h3 className="line-clamp-2 min-h-12 text-[15px] font-medium">{product.name}</h3><div className="mt-2 flex items-center gap-2"><span className="font-bold text-[#b45f06]">{formatCurrency(product.price)}</span>{product.compareAtPrice && <span className="text-xs text-[#999] line-through">{formatCurrency(product.compareAtPrice)}</span>}</div><div className="mt-2 flex gap-1">{product.colors.slice(0,3).map((c) => <span key={c.sku} className="h-3 w-3 rounded-full border" style={{ background: c.code }} />)}</div></div></div></Link>;
}

export function HomePage() {
  const [active, setActive] = useState(0);
  useEffect(() => { const id = window.setInterval(() => setActive((v) => (v + 1) % banners.length), 3500); return () => window.clearInterval(id); }, []);
  const featured = PRODUCTS.filter((p) => p.featured).slice(0, 8);
  const best = PRODUCTS.filter((p) => p.bestSeller).slice(0, 8);
  return <Shell><main className="mb-16 space-y-14"><section className="relative mx-auto max-w-[1920px]"><div className="relative aspect-[16/7] min-h-[280px] overflow-hidden bg-white">{banners.map((src, idx) => <div key={src} className={`absolute inset-0 transition-opacity duration-700 ${active === idx ? "opacity-100" : "opacity-0"}`}><Image src={src} alt="banner" fill className="object-contain" priority={idx===0} /></div>)}</div><div className="mt-3 flex justify-center gap-2">{banners.map((_, idx) => <button key={idx} onClick={() => setActive(idx)} className={`h-2.5 w-2.5 rounded-full ${active===idx ? "bg-[#444]" : "bg-[#d7d7d7]"}`} />)}</div></section><section className="container-shell"><div className="grid xs:grid-cols-2 md:grid-cols-4 gap-4">{[["Miễn phí vận chuyển","Miễn phí vận chuyển nội tỉnh Đồng Tháp"],["Đổi hàng 7 ngày","Hỗ trợ đổi size, đổi mẫu nhanh"],["Thanh toán COD","Nhận hàng rồi thanh toán"],["Hotline hỗ trợ","Tư vấn trực tiếp tại Cao Lãnh"]].map(([t,d]) => <div key={t} className="flex flex-col items-center rounded-lg p-5 text-center"><div className="flex h-12 w-12 items-center justify-center rounded-full border border-black text-xl">✦</div><p className="mb-2 mt-4 font-bold">{t}</p><p className="text-sm opacity-75">{d}</p></div>)}</div></section><HomeBlock title="Sản phẩm nổi bật" products={featured} /><HomeBlock title="Bán chạy tại cửa hàng" products={best} /><section className="container-shell grid gap-6 md:grid-cols-[1.2fr_0.8fr]"><div><h2 className="text-2xl font-bold uppercase">Câu chuyện của Tín Thành</h2><p className="mt-4 leading-7 text-[#666]">Phiên bản evolved này giữ lại vỏ giao diện trắng, header sticky, mega menu, hero banner và cảm giác retail dày đặc từ HTML tham chiếu, nhưng nâng cấp thành storefront có giỏ hàng, checkout, API sản phẩm/đơn hàng và trải nghiệm responsive dùng được thật.</p><div className="mt-4"><Link href="/cau-chuyen" className="border-b border-black pb-1 font-semibold">Xem thêm</Link></div></div><div className="border border-[#eee] p-5"><h3 className="font-bold">Hỗ trợ nhanh</h3><div className="mt-4 grid gap-3 text-sm"><a href={STORE.zalo} className="rounded border p-3">Đặt qua Zalo</a><a href={`tel:${STORE.hotline.replace(/\./g,"")}`} className="rounded border p-3">Gọi hotline {STORE.hotline}</a><Link href="/ho-tro/doi-tra" className="rounded border p-3">Xem chính sách đổi trả</Link></div></div></section></main></Shell>;
}

function HomeBlock({ title, products }: { title: string; products: Product[] }) {
  return <section className="container-shell"><div className="mb-5 flex items-end justify-between"><h2 className="text-2xl font-bold uppercase">{title}</h2><Link href="/tim-kiem" className="text-sm">Xem tất cả</Link></div><div className="grid grid-cols-2 gap-4 md:grid-cols-4">{products.map((p) => <ProductCard key={p.slug} product={p} />)}</div></section>;
}

export function ListingPage({ department, subcategory, search }: { department?: string; subcategory?: string; search?: string }) {
  const results = useMemo(() => PRODUCTS.filter((p) => (!department || p.department===department) && (!subcategory || p.subcategory===subcategory) && (!search || [p.name,p.description,...p.tags].join(" ").toLowerCase().includes(search.toLowerCase()))), [department, subcategory, search]);
  return <Shell><section className="container-shell py-8"><div className="mb-6"><p className="text-sm text-[#777]">Trang chủ / sản phẩm</p><h1 className="mt-2 text-3xl font-bold uppercase">{search ? `Kết quả cho "${search}"` : getDepartment(department || "")?.label || "Tất cả sản phẩm"}</h1></div><div className="grid gap-6 lg:grid-cols-[260px_1fr]"><aside className="space-y-5 border border-[#eee] p-5"><div><h2 className="font-bold">Danh mục</h2><div className="mt-3 grid gap-2 text-sm">{CATEGORIES.map((g) => <Link key={g.slug} href={`/danh-muc/${g.slug}`}>{g.label}</Link>)}</div></div><div><h2 className="font-bold">Bộ lọc nhanh</h2><div className="mt-3 grid gap-2 text-sm text-[#666]"><span>API hỗ trợ search, sort, department, subcategory, min/max price</span><span>UI giữ shell gọn theo HTML gốc</span></div></div></aside><div><div className="mb-4 flex items-center justify-between border border-[#eee] p-3 text-sm"><span>{results.length} sản phẩm</span><span>Sắp xếp: mới nhất / giá tăng / giá giảm</span></div><div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">{results.map((p) => <ProductCard key={p.slug} product={p} />)}</div></div></div></section></Shell>;
}

export function ProductPage({ slug }: { slug: string }) {
  const product = getProduct(slug);
  const { items, setItems } = useCart();
  const [variant, setVariant] = useState(product?.colors[0]?.sku || "");
  const [size, setSize] = useState(product?.sizes[0] || "");
  const [qty, setQty] = useState(1);
  if (!product) return <Shell><section className="container-shell py-16">Không tìm thấy sản phẩm.</section></Shell>;
  const related = PRODUCTS.filter((p) => p.slug !== product.slug && p.department === product.department).slice(0,4);
  return <Shell><section className="container-shell py-8"><div className="grid gap-8 lg:grid-cols-[1fr_0.9fr]"><div className="space-y-4"><div className="relative aspect-[4/5] border border-[#eee] bg-[#fafafa]"><Image src={product.images[0]} alt={product.name} fill className="object-cover" /></div></div><div><p className="text-sm text-[#777]">Trang chủ / {getDepartment(product.department)?.label} / {product.name}</p><h1 className="mt-2 text-3xl font-bold">{product.name}</h1><div className="mt-4 flex items-center gap-3"><span className="text-2xl font-bold text-[#b45f06]">{formatCurrency(product.price)}</span>{product.compareAtPrice && <span className="text-[#999] line-through">{formatCurrency(product.compareAtPrice)}</span>}</div><p className="mt-4 leading-7 text-[#666]">{product.description}</p><div className="mt-6"><p className="font-semibold">Màu sắc / SKU</p><div className="mt-2 flex flex-wrap gap-2">{product.colors.map((c) => <button key={c.sku} onClick={() => setVariant(c.sku)} className={`rounded border px-3 py-2 text-sm ${variant===c.sku ? "border-black" : "border-[#ddd]"}`}>{c.label} • {c.sku}</button>)}</div></div><div className="mt-6"><p className="font-semibold">Kích thước</p><div className="mt-2 flex flex-wrap gap-2">{product.sizes.map((s) => <button key={s} onClick={() => setSize(s)} className={`rounded border px-3 py-2 text-sm ${size===s ? "border-black bg-black text-white" : "border-[#ddd]"}`}>{s}</button>)}</div></div><div className="mt-6 flex items-center gap-3"><div className="flex items-center border"><button className="px-3 py-2" onClick={() => setQty((v) => Math.max(1, v-1))}>-</button><span className="px-4">{qty}</span><button className="px-3 py-2" onClick={() => setQty((v) => v+1)}>+</button></div><button onClick={() => setItems([...items, { slug: product.slug, variant, size, quantity: qty }])} className="bg-black px-6 py-3 text-white">Thêm vào giỏ</button><a href={STORE.zalo} className="border px-6 py-3">Đặt qua Zalo</a></div><div className="mt-6 grid gap-3 text-sm"><div className="border p-3">Miễn phí vận chuyển đơn từ 300K</div><div className="border p-3">Đổi hàng trong 7 ngày</div><div className="border p-3">COD toàn quốc</div></div></div></div></section><section className="container-shell"><h2 className="mb-5 text-2xl font-bold uppercase">Sản phẩm liên quan</h2><div className="grid grid-cols-2 gap-4 md:grid-cols-4">{related.map((p) => <ProductCard key={p.slug} product={p} />)}</div></section></Shell>;
}

export function CartPage() {
  const { items, setItems } = useCart();
  const rows = items.map((i, idx) => ({ ...i, idx, product: getProduct(i.slug)! })).filter((r) => r.product);
  const subtotal = rows.reduce((s, r) => s + r.product.price * r.quantity, 0);
  const shipping = rows.length ? (subtotal >= 300000 ? 0 : 30000) : 0;
  return <Shell><section className="container-shell py-8"><div className="grid gap-8 lg:grid-cols-[1fr_340px]"><div><h1 className="mb-5 text-3xl font-bold uppercase">Giỏ hàng</h1><div className="space-y-4">{rows.length ? rows.map((r) => <div key={r.idx} className="flex items-center justify-between border p-4"><div><h3 className="font-semibold">{r.product.name}</h3><p className="text-sm text-[#777]">{r.variant} • {r.size} • SL {r.quantity}</p></div><div className="text-right"><p className="font-bold">{formatCurrency(r.product.price * r.quantity)}</p><button className="mt-2 text-sm text-[#777] underline" onClick={() => setItems(items.filter((_, i) => i !== r.idx))}>Xóa</button></div></div>) : <div className="border p-6 text-[#777]">Chưa có sản phẩm trong giỏ.</div>}</div></div><div className="border p-5"><h2 className="text-xl font-bold">Tóm tắt đơn</h2><div className="mt-4 space-y-2 text-sm"><div className="flex justify-between"><span>Tạm tính</span><span>{formatCurrency(subtotal)}</span></div><div className="flex justify-between"><span>Vận chuyển</span><span>{formatCurrency(shipping)}</span></div><div className="flex justify-between border-t pt-3 font-bold"><span>Tổng</span><span>{formatCurrency(subtotal + shipping)}</span></div></div><Link href="/checkout" className="mt-5 block bg-black px-5 py-3 text-center text-white">Thanh toán</Link></div></div></section></Shell>;
}

export function CheckoutPage() {
  const { items, setItems } = useCart();
  const [error, setError] = useState("");
  async function submit(formData: FormData) {
    setError("");
    const payload = { customer: { firstName: formData.get("firstName"), lastName: formData.get("lastName"), email: formData.get("email"), phone: formData.get("phone"), address: formData.get("address"), city: formData.get("city"), postalCode: formData.get("postalCode") }, paymentMethod: formData.get("paymentMethod"), shippingMethod: formData.get("shippingMethod"), items, notes: formData.get("notes") };
    const res = await fetch("/api/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) return setError(data.error?.message || data.error || "Lỗi checkout");
    localStorage.setItem("last-order", JSON.stringify(data.order));
    setItems([]);
    window.location.href = "/dat-hang-thanh-cong";
  }
  return <Shell><section className="container-shell py-8"><div className="grid gap-8 lg:grid-cols-[1fr_360px]"><form action={submit} className="border p-5"><h1 className="text-3xl font-bold uppercase">Thanh toán</h1><p className="mt-2 text-sm text-[#777]">Checkout demo/staging nhưng dùng thật được trong local verification.</p><div className="mt-5 grid gap-4 sm:grid-cols-2">{["firstName","lastName","email","phone","address","city","postalCode"].map((f) => <input key={f} name={f} required={!["email","postalCode"].includes(f)} placeholder={f} className="border px-4 py-3" />)}</div><div className="mt-4 grid gap-4 sm:grid-cols-2"><select name="paymentMethod" className="border px-4 py-3"><option value="cod">COD</option><option value="bank-transfer">Chuyển khoản demo</option></select><select name="shippingMethod" className="border px-4 py-3"><option value="standard">Tiêu chuẩn</option><option value="express">Nhanh</option></select></div><textarea name="notes" className="mt-4 min-h-28 w-full border p-3" placeholder="Ghi chú giao hàng" />{error && <p className="mt-3 text-sm text-red-600">{error}</p>}<button className="mt-5 bg-black px-6 py-3 text-white">Xác nhận đơn hàng</button></form><div className="border p-5"><h2 className="text-xl font-bold">Thông tin đơn</h2><p className="mt-3 text-sm text-[#777]">{items.length} sản phẩm trong giỏ</p></div></div></section></Shell>;
}

export function SuccessPage() {
  const [order] = useState<StoredOrder>(() => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem("last-order");
    return raw ? (JSON.parse(raw) as StoredOrder) : null;
  });
  return <Shell><section className="container-shell py-16"><div className="mx-auto max-w-2xl border p-8 text-center"><h1 className="text-4xl font-bold uppercase">Đặt hàng thành công</h1><p className="mt-4 text-[#666]">Đơn hàng demo đã được tạo thành công và sẵn sàng cho staging verification.</p>{order && <div className="mt-6 border p-5 text-left"><p className="font-semibold">Mã đơn: {order.id}</p><p>Tổng đơn: {formatCurrency(order.total)}</p><p>Trạng thái: {order.status}</p></div>}<div className="mt-6 flex justify-center gap-3"><Link href="/" className="bg-black px-5 py-3 text-white">Về trang chủ</Link><Link href="/tim-kiem" className="border px-5 py-3">Tiếp tục mua sắm</Link></div></div></section></Shell>;
}

export function StoryPage() { return <Shell><section className="container-shell py-10"><h1 className="text-3xl font-bold uppercase">Câu chuyện của Tín Thành</h1><div className="mt-5 max-w-3xl space-y-4 leading-7 text-[#666]"><p>Shop Tín Thành là cửa hàng thời trang địa phương quen thuộc tại Cao Lãnh, Đồng Tháp, nổi bật bởi cách trưng bày sáng, rõ, nhiều danh mục và cảm giác mua sắm thực dụng.</p><p>Phiên bản evolved này đi theo sát shell của HTML snapshot: sticky white header, mega menu nhiều nhóm, hero banner, dải trust service, product grid dày và footer chính sách/hỗ trợ.</p><p>Điểm nâng cấp là toàn bộ luồng thương mại điện tử đã hoàn chỉnh hơn: listing, search, PDP, cart, checkout, success và API mock bền cho staging.</p></div></section></Shell>; }

export function BlogPage() { return <Shell><section className="container-shell py-10"><h1 className="text-3xl font-bold uppercase">Blog</h1><div className="mt-6 grid gap-4 md:grid-cols-3">{BLOG_POSTS.map((p) => <article key={p.slug} className="border p-5"><p className="text-xs text-[#777]">{p.date}</p><h2 className="mt-2 text-xl font-bold">{p.title}</h2><p className="mt-3 text-[#666]">{p.excerpt}</p></article>)}</div></section></Shell>; }

export function SupportPage({ title, paragraphs }: { title: string; paragraphs: string[] }) { return <Shell><section className="container-shell py-10"><h1 className="text-3xl font-bold uppercase">{title}</h1><div className="mt-5 max-w-3xl space-y-4 leading-7 text-[#666]">{paragraphs.map((p) => <p key={p}>{p}</p>)}</div></section></Shell>; }
