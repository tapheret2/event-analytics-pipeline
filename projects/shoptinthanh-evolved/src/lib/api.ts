import { CATEGORIES, PRODUCTS, STORE, type Product } from "@/lib/store-data";

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

interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: string[];
  };
}

const FREE_SHIPPING_THRESHOLD = 300_000;
const STANDARD_SHIPPING = 30_000;
const EXPRESS_SHIPPING = 45_000;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^(0|\+84)\d{9,10}$/;

const seededOrders: OrderRecord[] = [
  {
    id: "TT-260330-001",
    status: "processing",
    createdAt: "2026-03-30T07:40:00.000Z",
    customer: {
      firstName: "Phát",
      lastName: "Phạm",
      email: "phat@example.com",
      phone: "0901234567",
      address: "52 đường Tháp Mười",
      city: "Cao Lãnh",
      postalCode: "870000",
    },
    paymentMethod: "cod",
    shippingMethod: "standard",
    notes: "Khách cần gọi trước khi giao.",
    items: [
      {
        slug: "ao-polo-nam-basic",
        name: "Áo Polo Nam Basic",
        variant: "APN01-N",
        color: "Xanh navy",
        size: "L",
        quantity: 1,
        price: 159000,
        lineTotal: 159000,
      },
      {
        slug: "non-bucket-unisex",
        name: "Nón Bucket Unisex",
        variant: "NON01-BK",
        color: "Đen",
        size: "Free size",
        quantity: 2,
        price: 89000,
        lineTotal: 178000,
      },
    ],
    subtotal: 337000,
    shipping: 0,
    tax: 0,
    total: 337000,
  },
];

const globalStore = globalThis as typeof globalThis & {
  __shoptinThanhEvolvedOrders__?: OrderRecord[];
};

const orderStore = globalStore.__shoptinThanhEvolvedOrders__ ?? [...seededOrders];
globalStore.__shoptinThanhEvolvedOrders__ = orderStore;

function normalize(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function parseNumber(value: string | null, fallback: number) {
  if (value === null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function unique<T>(values: T[]) {
  return [...new Set(values)];
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
    case "newest":
      return [...products].sort((a, b) => Number(Boolean(b.isNew)) - Number(Boolean(a.isNew)) || a.name.localeCompare(b.name, "vi"));
    case "featured":
      return [...products].sort((a, b) => Number(Boolean(b.featured)) - Number(Boolean(a.featured)) || a.price - b.price);
    default:
      return products;
  }
}

function buildFilters(products: Product[]) {
  return {
    departments: unique(products.map((product) => product.department)).sort((a, b) => a.localeCompare(b, "vi")),
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

export function getCategoriesPayload() {
  return {
    categories: CATEGORIES,
    total: CATEGORIES.length,
  };
}

export function getProductBySlug(slug: string) {
  return PRODUCTS.find((product) => product.slug === slug);
}

export function listProducts(searchParams: URLSearchParams) {
  const department = normalize(searchParams.get("department"));
  const subcategory = normalize(searchParams.get("subcategory"));
  const search = normalize(searchParams.get("search")).toLowerCase();
  const sort = normalize(searchParams.get("sort")) || "default";
  const minPrice = parseNumber(searchParams.get("minPrice"), 0);
  const maxPrice = parseNumber(searchParams.get("maxPrice"), Number.MAX_SAFE_INTEGER);

  const appliedFilters = {
    department,
    subcategory,
    search,
    sort,
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

  const products = PRODUCTS.filter((product) => {
    const searchable = [product.name, product.description, product.subcategory, ...product.tags].join(" ").toLowerCase();

    return (
      (!department || product.department === department) &&
      (!subcategory || product.subcategory === subcategory) &&
      (!search || searchable.includes(search)) &&
      product.price >= minPrice &&
      product.price <= maxPrice
    );
  });

  return {
    ok: true as const,
    body: {
      products: sortProducts(products, sort),
      total: products.length,
      filters: buildFilters(products),
      appliedFilters,
    },
  };
}

function validateCustomer(customer: unknown) {
  const value = (customer ?? {}) as Partial<CheckoutCustomer>;
  const result: CheckoutCustomer = {
    firstName: normalize(value.firstName),
    lastName: normalize(value.lastName),
    email: normalize(value.email) || undefined,
    phone: normalize(value.phone),
    address: normalize(value.address),
    city: normalize(value.city),
    postalCode: normalize(value.postalCode) || undefined,
  };

  const issues: string[] = [];

  if (!result.firstName) issues.push("customer.firstName là bắt buộc.");
  if (!result.lastName) issues.push("customer.lastName là bắt buộc.");
  if (!result.phone) issues.push("customer.phone là bắt buộc.");
  if (result.phone && !PHONE_REGEX.test(result.phone.replace(/[\s.()-]/g, ""))) issues.push("customer.phone không đúng định dạng số điện thoại Việt Nam.");
  if (!result.address) issues.push("customer.address là bắt buộc.");
  if (!result.city) issues.push("customer.city là bắt buộc.");
  if (result.email && !EMAIL_REGEX.test(result.email)) issues.push("customer.email không đúng định dạng.");

  return { customer: result, issues };
}

function validateLineItem(item: CheckoutItemInput, index: number) {
  const slug = normalize(item.slug);
  const variant = normalize(item.variant);
  const size = normalize(item.size);
  const quantity = Number(item.quantity);
  const product = getProductBySlug(slug);

  if (!product) return { issue: `items[${index}] tham chiếu slug không tồn tại.`, product: null, colorLabel: "" };
  if (!variant) return { issue: `items[${index}].variant là bắt buộc.`, product, colorLabel: "" };
  const color = product.colors.find((entry) => entry.sku === variant);
  if (!color) return { issue: `items[${index}].variant không khớp SKU của sản phẩm ${slug}.`, product, colorLabel: "" };
  if (!size) return { issue: `items[${index}].size là bắt buộc.`, product, colorLabel: color.label };
  if (!product.sizes.includes(size)) return { issue: `items[${index}].size không tồn tại cho sản phẩm ${slug}.`, product, colorLabel: color.label };
  if (!Number.isInteger(quantity) || quantity < 1) return { issue: `items[${index}].quantity phải là số nguyên dương.`, product, colorLabel: color.label };

  return { issue: null, product, colorLabel: color.label };
}

export function createOrder(payload: unknown) {
  const value = (payload ?? {}) as Partial<CheckoutPayload>;
  const items = Array.isArray(value.items) ? value.items : [];
  const paymentMethod = normalize(value.paymentMethod as string) as CheckoutPaymentMethod;
  const shippingMethod = normalize(value.shippingMethod as string) as CheckoutShippingMethod;
  const notes = normalize(value.notes);

  const { customer, issues } = validateCustomer(value.customer);

  if (!items.length) issues.push("items phải có ít nhất 1 sản phẩm.");
  if (paymentMethod !== "cod" && paymentMethod !== "bank-transfer") issues.push("paymentMethod chỉ hỗ trợ cod hoặc bank-transfer.");
  if (shippingMethod !== "standard" && shippingMethod !== "express") issues.push("shippingMethod chỉ hỗ trợ standard hoặc express.");

  const orderItems: OrderItem[] = [];

  items.forEach((item, index) => {
    const result = validateLineItem(item as CheckoutItemInput, index);
    if (result.issue || !result.product) {
      if (result.issue) issues.push(result.issue);
      return;
    }

    const quantity = Number((item as CheckoutItemInput).quantity);
    orderItems.push({
      slug: result.product.slug,
      name: result.product.name,
      variant: normalize((item as CheckoutItemInput).variant),
      color: result.colorLabel,
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

  const subtotal = orderItems.reduce((sum, item) => sum + item.lineTotal, 0);
  const shipping = subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : shippingMethod === "express" ? EXPRESS_SHIPPING : STANDARD_SHIPPING;
  const tax = 0;
  const total = subtotal + shipping + tax;

  const order: OrderRecord = {
    id: `TT-${new Date().toISOString().slice(2, 10).replace(/-/g, "")}-${String(orderStore.length + 1).padStart(3, "0")}`,
    status: "confirmed",
    createdAt: new Date().toISOString(),
    customer,
    paymentMethod,
    shippingMethod,
    notes,
    items: orderItems,
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

export function getHealthPayload() {
  return {
    ok: true,
    service: "shoptinthanh-evolved",
    timestamp: new Date().toISOString(),
    catalog: {
      products: PRODUCTS.length,
      orders: orderStore.length,
      departments: CATEGORIES.length,
    },
    store: {
      name: STORE.name,
      hotline: STORE.hotline,
      address: STORE.address,
    },
  };
}

export function apiError(status: number, code: string, message: string, details?: string[]) {
  const body: ApiErrorBody = {
    error: {
      code,
      message,
      details: details?.length ? details : undefined,
    },
  };

  return Response.json(body, { status });
}
