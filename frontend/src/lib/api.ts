export const API_BASE =
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

const API_KEY: string = import.meta.env.VITE_API_KEY ?? "";

/** Fetch wrapper that auto-injects the API key header. */
export async function apiFetch(
  url: string,
  init?: RequestInit
): Promise<Response> {
  return fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...(init?.headers ?? {}),
    },
  });
}

/** Fetch + parse JSON, with error handling. */
export async function apiFetchJson<T>(
  url: string,
  init?: RequestInit
): Promise<T> {
  const res = await apiFetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Request failed ${res.status} ${res.statusText}: ${text}`
    );
  }
  return res.json();
}
