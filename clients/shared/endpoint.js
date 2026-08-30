export function normalizeSadEndpoint(value) {
  const raw = String(value || "").trim().replace(/\/+$/, "");
  if (!raw) throw new Error("SAD endpoint is required");
  const url = new URL(raw);
  const loopback = ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
  if (url.username || url.password || url.search || url.hash) throw new Error("Endpoint must not contain credentials, query, or fragment");
  if (loopback) {
    if (url.protocol !== "http:") throw new Error("Loopback SAD endpoints use HTTP");
  } else if (url.protocol !== "https:") {
    throw new Error("Remote SAD endpoints require HTTPS");
  }
  return raw;
}

export function apiUrl(endpoint, path = "") {
  const base = normalizeSadEndpoint(endpoint);
  return `${base}/${String(path).replace(/^\/+/, "")}`.replace(/\/$/, path ? "" : "/");
}
