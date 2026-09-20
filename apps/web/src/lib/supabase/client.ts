import { createBrowserClient } from "@supabase/ssr";

/**
 * Creates and returns a singleton-like Supabase client for Client Components.
 * Utilizes the browser's cookie storage and real-time WebSocket channels.
 */
export function createClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing Supabase environment variables: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set in .env.local"
    );
  }

  return createBrowserClient(supabaseUrl, supabaseAnonKey);
}
