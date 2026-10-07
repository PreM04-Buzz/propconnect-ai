import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

type S = components["schemas"];
export type User = S["UserRead"];
export type UserCreate = S["UserCreate"];
export type UserRole = User["role"];
export type ClientListItem = S["ClientListItem"];
export type ClientDetail = S["ClientDetail"];
export type ClientCreate = S["ClientCreate"];
export type ClientUpdate = S["ClientUpdate"];
export type InteractionType = S["InteractionType"];
export type Property = S["PropertyRead"];
export type PropertyCreate = S["PropertyCreate"];
export type PropertyMatch = S["PropertyMatch"];
export type CityCount = S["CityCount"];
export type LeadCard = S["LeadCard"];
export type LeadDetail = S["LeadDetail"];
export type LeadStage = S["LeadStage"];
export type StageCount = S["StageCount"];
export type Suggestion = S["SuggestionRead"];
export type FinancingStatus = S["FinancingStatus"];
export type ClientType = S["ClientType"];

// Access token lives in sessionStorage: it survives a refresh but is cleared when the tab closes.
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
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, "");
  }
  return fallback;
}
