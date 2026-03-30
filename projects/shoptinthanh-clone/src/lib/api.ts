import { CATEGORIES, PRODUCTS, STORE_INFO, type Product, type ProductColor } from "@/lib/store-data";

export type CheckoutPaymentMethod = "cod" | "bank-transfer";
export type CheckoutShippingMethod = "standard" | "express";
export type OrderStatus = "confirmed" | "processing" | "shipped" | "delivered" | "cancelled";

export interface CheckoutCustomer {
  firstName: string;
  lastName: string;
  email?: string;
  phone: string;
  address: string;
  city: string;
  postalCode?: string;
}

export interface CheckoutItemInput {
  slug: string;
  variant: string;
  size: string;
  quantity: number;
}

export interface CheckoutPayload {
  customer: CheckoutCustomer;
  paymentMethod: CheckoutPaymentMethod;
  shippingMethod: CheckoutShippingMethod;
  items: CheckoutItemInput[];
  notes?: string;
}

export interface OrderItem {
  slug: string;
  name: string;
  variant: string;
  color: string;
  size: string;
  quantity: number;
  price: number;
  lineTotal: number;
}

export interface OrderRecord {
  id: string;
  status: OrderStatus;
  createdAt: string;
  customer: CheckoutCustomer;
  paymentMethod: CheckoutPaymentMethod;
  shippingMethod: CheckoutShippingMethod;
  notes: string;
  items: OrderItem[];
  subtotal: number;
  shipping: number;
  tax: number;
  total: number;
}

interface ApiErrorShape {
  error: {
    code: string;
    message: string;
    details?: string[];
  };
}

const SHIPPING_THRESHOLD = 300_000;
const SHIPPING_STANDARD = 30_000;
const SHIPPING_EXPRESS = 45_000;
const TAX_RATE = 0;
const PHONE_REGEX = /^(0|\+84)\d{9,10}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const seedOrders: OrderRecord[] = [
  {
    id: "TT-260329-001",
    status: "delivered",
    createdAt: "2026-03-29T02:15:00.000Z",
    customer: {
      firstName: "Minh",
      lastName: "Nguyễn",
      email: "minh.nguyen@example.com",
      phone: "0901234567",
      address: "52 đường Tháp Mười",
      city: STORE_INFO.city,
      postalCode: "870000",
    },
    paymentMethod: "cod",
    shippingMethod: "standard",
    notes: "Khách quen lấy size L chuẩn form.",
    items: [
      {
        slug: "ao-thun-polo-nam-mau",
        name: "Áo Thun Polo Nam Màu Trơn",
        variant: "ATN0048-XN",
        color: "Xanh navy",
        size: "L",
        quantity: 1,
        price: 159000,
        lineTotal: 159000,
      },
      {
        slug: "that-lung-da-nam-khoa-kim",
        name: "Thắt Lưng Da Nam Khóa Kim",
        variant: "TL0010-DN",
        color: "Đen",
        size: "110cm",
        quantity: 1,
        price: 149000,
        lineTotal: 149000,
      },
    ],
    subtotal: 308000,
    shipping: 0,
    tax: 0,
    total: 308000,
  },
];

const globalStore = globalThis as typeof globalThis & {
  __shoptinThanhOrders__?: OrderRecord[];
};

const orderStore = globalStore.__shoptinThanhOrders__ ?? [...seedOrders];
globalStore.__shoptinThanhOrders__ = orderStore;

function normalize(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function parseNumber(value: string | null, fallback: number) {
  if (value === null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function unique<T>(items: T[]) {
  return [...new Set(items)];
}

function sortProducts(products: Product[], sort: string) {
  switch (sort) {
    case "price_asc":
      return [...products].sort((a, b) => a.price - b.price);
    case "price_desc":
      return [...products].sort((a, b) => b.price - a.price);
    case "name_asc":
      return [...products].sort((a, b) => a.name.localeCompare(b.name, "vi"));
    case "name_desc":
      return [...products].sort((a, b) => b.name.localeCompare(a.name, "vi"));
    case "featured":
      return [...products].sort((a, b) => Number(b.featured) - Number(a.featured) || a.price - b.price);
    case "newest":
      return [...products].sort((a, b) => Number(Boolean(b.isNew)) - Number(Boolean(a.isNew)) || a.name.localeCompare(b.name, "vi"));
    default:
      return products;
  }
}

function buildFilterSummary(products: Product[]) {
  return {
    departments: unique(products.map((product) => product.department)).sort((a, b) => a.localeCompare(b, "vi")),
    categories: unique(products.map((product) => product.category)).sort((a, b) => a.localeCompare(b, "vi")),
    subcategories: unique(products.map((product) => product.subcategory)).sort((a, b) => a.localeCompare(b, "vi")),
    colors: unique(products.flatMap((product) => product.colors.map((color) => color.label))).sort((a, b) => a.localeCompare(b, "vi")),
    sizes: unique(products.flatMap((product) => product.sizes)).sort((a, b) => a.localeCompare(b, "vi", { numeric: true })),
    priceRange: {
      min: products.length ? Math.min(...products.map((product) => product.price)) : 0,
      max: products.length ? Math.max(...products.map((product) => product.price)) : 0,
    },
    sortOptions: ["default", "featured", "newest", "price_asc", "price_desc", "name_asc", "name_desc"],
  };
}

export function listProducts(searchParams: URLSearchParams) {
  const department = normalize(searchParams.get("department"));
  const category = normalize(searchParams.get("category"));
  const subcategory = normalize(searchParams.get("subcategory"));
  const search = normalize(searchParams.get("search")).toLowerCase();
  const sort = normalize(searchParams.get("sort")) || "default";
  const color = normalize(searchParams.get("color")).toLowerCase();
  const size = normalize(searchParams.get("size"));
  const minPrice = parseNumber(searchParams.get("minPrice"), 0);
  const maxPrice = parseNumber(searchParams.get("maxPrice"), Number.MAX_SAFE_INTEGER);

  const requestedFilters = {
    department,
    category,
    subcategory,
    search,
    sort,
    color,
    size,
    minPrice: Number.isFinite(minPrice) ? minPrice : null,
    maxPrice: Number.isFinite(maxPrice) ? maxPrice : null,
  };

  if (!Number.isFinite(minPrice) || !Number.isFinite(maxPrice) || minPrice < 0 || maxPrice < 0 || minPrice > maxPrice) {
    return {
      ok: false as const,
      response: apiError(422, "INVALID_PRICE_RANGE", "Khoảng giá không hợp lệ.", [
        "minPrice và maxPrice phải là số hợp lệ, không âm, và minPrice không được lớn hơn maxPrice.",
      ]),
    };
  }

  const filtered = PRODUCTS.filter((product) => {
    const searchable = [
      product.name,
      product.description,
      product.brand,
      product.category,
      product.subcategory,
      ...product.tags,
    ]
      .join(" ")
      .toLowerCase();

    return (
      (!department || product.department === department) &&
      (!category || product.category === category) &&
      (!subcategory || product.subcategory === subcategory) &&
      (!search || searchable.includes(search)) &&
      (!color || product.colors.some((item) => item.label.toLowerCase().includes(color) || item.sku.toLowerCase().includes(color))) &&
      (!size || product.sizes.includes(size)) &&
      product.price >= minPrice &&
      product.price <= maxPrice
    );
  });

  return {
    ok: true as const,
    body: {
      products: sortProducts(filtered, sort),
      total: filtered.length,
      filters: buildFilterSummary(filtered),
      appliedFilters: requestedFilters,
    },
  };
}

export function getProductBySlug(slug: string) {
  return PRODUCTS.find((product) => product.slug === slug);
}

export function getCategoriesPayload() {
  return {
    categories: CATEGORIES,
    total: CATEGORIES.length,
  };
}

function validateCustomer(customer: unknown) {
  const data = (customer ?? {}) as Partial<CheckoutCustomer>;
  const firstName = normalize(data.firstName);
  const lastName = normalize(data.lastName);
  const email = normalize(data.email);
  const phone = normalize(data.phone);
  const address = normalize(data.address);
  const city = normalize(data.city) || STORE_INFO.city;
  const postalCode = normalize(data.postalCode);

  const issues: string[] = [];

  if (!firstName) issues.push("customer.firstName là bắt buộc.");
  if (!lastName) issues.push("customer.lastName là bắt buộc.");
  if (!phone) issues.push("customer.phone là bắt buộc.");
  if (phone && !PHONE_REGEX.test(phone.replace(/[\s.()-]/g, ""))) issues.push("customer.phone không đúng định dạng số điện thoại Việt Nam.");
  if (!address) issues.push("customer.address là bắt buộc.");
  if (!city) issues.push("customer.city là bắt buộc.");
  if (email && !EMAIL_REGEX.test(email)) issues.push("customer.email không đúng định dạng.");

  return {
    issues,
    customer: { firstName, lastName, email: email || undefined, phone, address, city, postalCode: postalCode || undefined },
  };
}

function validateItem(item: CheckoutItemInput, index: number) {
  const product = getProductBySlug(normalize(item.slug));
  if (!product) return { issue: `items[${index}] tham chiếu slug không tồn tại.`, product: null, color: null as ProductColor | null };

  const variant = normalize(item.variant);
  const size = normalize(item.size);
  const quantity = Number(item.quantity);
  const color = product.colors.find((entry) => entry.sku === variant);

  if (!variant) return { issue: `items[${index}].variant là bắt buộc.`, product, color: null as ProductColor | null };
  if (!color) return { issue: `items[${index}].variant không khớp SKU của sản phẩm ${product.slug}.`, product, color: null as ProductColor | null };
  if (!size) return { issue: `items[${index}].size là bắt buộc.`, product, color };
  if (!product.sizes.includes(size)) return { issue: `items[${index}].size không tồn tại cho sản phẩm ${product.slug}.`, product, color };
  if (!Number.isInteger(quantity) || quantity < 1) return { issue: `items[${index}].quantity phải là số nguyên dương.`, product, color };
  if (!product.availability) return { issue: `items[${index}] hiện đang hết hàng.`, product, color };

  return { issue: null, product, color };
}

export function createOrder(payload: unknown) {
  const data = (payload ?? {}) as Partial<CheckoutPayload>;
  const paymentMethod = normalize(data.paymentMethod as string) as CheckoutPaymentMethod;
  const shippingMethod = normalize(data.shippingMethod as string) as CheckoutShippingMethod;
  const notes = normalize(data.notes);
  const items = Array.isArray(data.items) ? data.items : [];

  const issues: string[] = [];
  const customerResult = validateCustomer(data.customer);
  issues.push(...customerResult.issues);

  if (!items.length) issues.push("items phải có ít nhất 1 sản phẩm.");
  if (paymentMethod !== "cod" && paymentMethod !== "bank-transfer") issues.push("paymentMethod chỉ hỗ trợ cod hoặc bank-transfer.");
  if (shippingMethod !== "standard" && shippingMethod !== "express") issues.push("shippingMethod chỉ hỗ trợ standard hoặc express.");

  const validatedItems: OrderItem[] = [];

  items.forEach((item, index) => {
    const result = validateItem(item as CheckoutItemInput, index);
    if (result.issue || !result.product || !result.color) {
      if (result.issue) issues.push(result.issue);
      return;
    }

    const quantity = Number((item as CheckoutItemInput).quantity);
    validatedItems.push({
      slug: result.product.slug,
      name: result.product.name,
      variant: result.color.sku,
      color: result.color.label,
      size: normalize((item as CheckoutItemInput).size),
      quantity,
      price: result.product.price,
      lineTotal: result.product.price * quantity,
    });
  });

  if (issues.length) {
    return {
      ok: false as const,
      response: apiError(422, "CHECKOUT_VALIDATION_FAILED", "Dữ liệu checkout không hợp lệ.", issues),
    };
  }

  const subtotal = validatedItems.reduce((sum, item) => sum + item.lineTotal, 0);
  const shippingBase = shippingMethod === "express" ? SHIPPING_EXPRESS : SHIPPING_STANDARD;
  const shipping = subtotal >= SHIPPING_THRESHOLD ? 0 : shippingBase;
  const tax = Math.round(subtotal * TAX_RATE);
  const total = subtotal + shipping + tax;
  const createdAt = new Date().toISOString();
  const order: OrderRecord = {
    id: `TT-${new Date().toISOString().slice(2, 10).replace(/-/g, "")}-${String(orderStore.length + 1).padStart(3, "0")}`,
    status: "confirmed",
    createdAt,
    customer: customerResult.customer,
    paymentMethod,
    shippingMethod,
    notes,
    items: validatedItems,
    subtotal,
    shipping,
    tax,
    total,
  };

  orderStore.unshift(order);

  return {
    ok: true as const,
    body: { order },
  };
}

export function listOrders() {
  return {
    orders: orderStore,
    total: orderStore.length,
  };
}

export function apiError(status: number, code: string, message: string, details?: string[]) {
  const body: ApiErrorShape = {
    error: {
      code,
      message,
      details: details?.length ? details : undefined,
    },
  };

  return Response.json(body, { status });
}
