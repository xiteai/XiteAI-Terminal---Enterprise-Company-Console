// The one door to the server. Every call carries the console header (the
// server's cross-site guard), and while the founder previews a lower level,
// the preview header too, so the server answers as that level would see it.

let previewLevel = null;
let onUnauthorized = null;

export const setPreview = (level) => { previewLevel = level || null; };
export const getPreview = () => previewLevel;
export const setOnUnauthorized = (fn) => { onUnauthorized = fn; };

export class ApiError extends Error {
  constructor(status, detail) {
    const message = typeof detail === "string" ? detail : detail?.message || "Something went wrong. Please try again.";
    super(message);
    this.status = status;
    this.field = typeof detail === "object" && detail ? detail.field : undefined;
  }
}

async function request(method, path, body) {
  const headers = { "X-TC": "1" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (previewLevel) headers["X-TC-Preview"] = previewLevel;
  let res;
  try {
    res = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection.");
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = { detail: text }; }
  }
  if (!res.ok) {
    const err = new ApiError(res.status, data?.detail ?? res.statusText);
    err.needCode = Boolean(data?.need_code);
    if (res.status === 401 && onUnauthorized && !path.startsWith("/api/auth/login")) onUnauthorized();
    throw err;
  }
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body = {}) => request("POST", path, body),
  put: (path, body = {}) => request("PUT", path, body),
  patch: (path, body = {}) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),
};

export const qs = (params) => {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") s.set(k, v); });
  const out = s.toString();
  return out ? `?${out}` : "";
};
