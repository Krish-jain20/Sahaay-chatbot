import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// Only the publishable (anon) key is ever used in the browser. The secret key stays on the server.
let client: SupabaseClient | null = null;

export function supabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return null;
  client ??= createClient(url, key, { auth: { persistSession: true, autoRefreshToken: true } });
  return client;
}

/** Returns a valid access token, signing in as a guest (anonymous user) the first time. */
export async function getAccessToken(): Promise<string | null> {
  const sb = supabase();
  if (!sb) return null;
  const { data } = await sb.auth.getSession();
  if (data.session) return data.session.access_token;
  const { data: anon, error } = await sb.auth.signInAnonymously();
  if (error) return null;
  return anon.session?.access_token ?? null;
}

export interface AccountState {
  configured: boolean;
  email: string | null;
  guest: boolean;
}

export async function accountState(): Promise<AccountState> {
  const sb = supabase();
  if (!sb) return { configured: false, email: null, guest: true };
  const { data } = await sb.auth.getUser();
  const user = data.user;
  return { configured: true, email: user?.email ?? null, guest: !user || user.is_anonymous === true || !user.email };
}

/**
 * Emails a sign-in link. A guest is upgraded in place (same user id, so their saved details and
 * cases stay); someone with no session at all gets a normal magic link.
 */
export async function sendSignInLink(email: string): Promise<boolean> {
  const sb = supabase();
  if (!sb) return false;
  const redirect = typeof window === "undefined" ? undefined : `${window.location.origin}/privacy`;
  const { data } = await sb.auth.getSession();
  if (data.session?.user.is_anonymous) {
    const { error } = await sb.auth.updateUser({ email }, { emailRedirectTo: redirect });
    return !error;
  }
  const { error } = await sb.auth.signInWithOtp({ email, options: { emailRedirectTo: redirect } });
  return !error;
}

export async function signOut(): Promise<void> {
  await supabase()?.auth.signOut();
}
