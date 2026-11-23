import { API_URL } from "@/lib/sse";
import { getAccessToken } from "@/lib/supabase";

async function authed(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
}

export interface SavedFact {
  key: string;
  value: unknown;
  confirmed: boolean;
}

export async function loadFacts(): Promise<Record<string, unknown>> {
  const res = await authed("/me/facts");
  if (!res.ok) return {};
  const rows = (await res.json()) as SavedFact[];
  return Object.fromEntries(rows.filter((r) => r.confirmed).map((r) => [r.key, r.value]));
}

export async function saveFacts(facts: Record<string, unknown>): Promise<boolean> {
  const results = await Promise.all(
    Object.entries(facts).map(([key, value]) =>
      authed("/me/facts", { method: "PUT", body: JSON.stringify({ key, value, source: "user_said", confirmed: true, consent: true }) }),
    ),
  );
  return results.every((r) => r.ok);
}

export async function deleteMyData(): Promise<boolean> {
  return (await authed("/me/data", { method: "DELETE" })).ok;
}

export async function reportIncorrect(serviceId: string, note: string): Promise<boolean> {
  return (await authed("/reports/incorrect", { method: "POST", body: JSON.stringify({ service_id: serviceId, note }) })).ok;
}
