import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { createSafeStorage } from './safeStorage';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim();

export const supabaseConfigured = Boolean(
  supabaseUrl && publishableKey && /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(supabaseUrl),
);

function getBrowserStorage(): Storage | undefined {
  try { return window.sessionStorage; }
  catch { return undefined; }
}

export const supabase: SupabaseClient | null = supabaseConfigured
  ? createClient(supabaseUrl!, publishableKey!, {
      auth: {
        storage: createSafeStorage(getBrowserStorage()),
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: 'pkce',
      },
    })
  : null;
