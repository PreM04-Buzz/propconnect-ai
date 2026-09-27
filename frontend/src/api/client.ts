import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

export type User = components["schemas"]["UserRead"];
export type UserCreate = components["schemas"]["UserCreate"];
export type UserRole = User["role"];

// Access token lives in sessionStorage: it survives a refresh but is cleared when
// the tab closes. (Phase 7 hardening option: move to an httpOnly cookie.)
const TOKEN_KEY = "propconnect.token";
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

const auth: Middleware = {
  onRequest({ request }) {
    const token = tokenStore.get();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401 && tokenStore.get()) {
      tokenStore.clear();
      onUnauthorized();
    }
    return response;
  },
};

/** Typed client: paths, params and response bodies all come from FastAPI's OpenAPI schema. */
export const api = createClient<paths>({ baseUrl: "" });
api.use(auth);

export function errorMessage(error: unknown, fallback = "Something went wrong. Try again."): string {
  if (error && typeof error === "object" && "detail" in error) {
    const d = (error as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg);
  }
  return fallback;
}
