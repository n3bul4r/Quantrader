export async function api<T = any>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  const res = await fetch(`/api${path}`, {
    ...rest,
    headers: json !== undefined ? { "Content-Type": "application/json", ...(rest.headers ?? {}) } : rest.headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const usd = (x: number | null | undefined, d = 0) =>
  x === null || x === undefined || Number.isNaN(x)
    ? "—"
    : `${x < 0 ? "−" : ""}$${Math.abs(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;

export const pct = (x: number | null | undefined, d = 0) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : `${(x * 100).toFixed(d)}%`;

export const num = (x: number | null | undefined, d = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : x.toFixed(d);

export const signClass = (x: number | null | undefined) =>
  x === null || x === undefined ? "" : x > 0 ? "text-pos" : x < 0 ? "text-neg" : "";
