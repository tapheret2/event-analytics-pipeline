import { siteContent } from "@/lib/site-content";

const APP_VERSION = "0.1.0";

export function buildMeta() {
  return {
    generatedAt: new Date().toISOString(),
    environment: process.env.NODE_ENV || "development",
    version: APP_VERSION,
  };
}

export function buildSitePayload() {
  return {
    meta: buildMeta(),
    ...siteContent,
  };
}

export function buildAcceptedContactPayload(submissionId: string) {
  return {
    data: {
      accepted: true,
      submissionId,
      receivedAt: new Date().toISOString(),
    },
    meta: buildMeta(),
  };
}

export function buildErrorPayload(code: string, message: string, details?: unknown) {
  return {
    error: {
      code,
      message,
      ...(details ? { details } : {}),
    },
    meta: buildMeta(),
  };
}

export function validateContactPayload(body: unknown) {
  if (!body || typeof body !== "object") {
    throw createValidationError("Request body must be a JSON object");
  }

  const record = body as Record<string, unknown>;
  const requiredFields = ["name", "email", "message"];

  for (const field of requiredFields) {
    const value = typeof record[field] === "string" ? record[field].trim() : "";
    if (!value) {
      throw createValidationError(`${field} is required`, { field });
    }
  }

  const email = String(record.email).trim();
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(email)) {
    throw createValidationError("Email must be valid", { field: "email" });
  }

  const normalized = {
    name: String(record.name).trim(),
    email,
    company: typeof record.company === "string" ? record.company.trim() : "",
    projectType: typeof record.projectType === "string" ? record.projectType.trim() : "",
    budget: typeof record.budget === "string" ? record.budget.trim() : "",
    timeline: typeof record.timeline === "string" ? record.timeline.trim() : "",
    message: String(record.message).trim(),
  };

  if (normalized.message.length < 10) {
    throw createValidationError("Message must be at least 10 characters", { field: "message" });
  }

  return normalized;
}

function createValidationError(message: string, details?: unknown) {
  const error = new Error(message) as Error & { status?: number; code?: string; details?: unknown };
  error.status = 400;
  error.code = "VALIDATION_ERROR";
  error.details = details;
  return error;
}
