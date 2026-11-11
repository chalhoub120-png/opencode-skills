import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import { AuthForm } from '../features/auth/AuthForm';
import { WorkspacePage } from '../features/workspaces/WorkspacePage';
import { getCurrentSession, signOut } from '../features/auth/authService';
import { supabase, supabaseConfigured } from '../lib/supabase';

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    if (!supabase) {
      setCheckingSession(false);
      return;
    }
    let mounted = true;
    let authEventSeen = false;
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      authEventSeen = true;
      if (mounted) {
        setUser(session?.user ?? null);
        setCheckingSession(false);
      }
    });
    void getCurrentSession()
      .then((session) => { if (mounted && !authEventSeen) setUser(session?.user ?? null); })
      .catch((error: unknown) => { if (mounted) setAuthError(error instanceof Error ? error.message : 'Could not restore your session.'); })
      .finally(() => { if (mounted) setCheckingSession(false); });
    return () => { mounted = false; listener.subscription.unsubscribe(); };
  }, []);

  async function handleSignOut() {
    setAuthError('');
    try { await signOut(); setUser(null); }
    catch (error) { setAuthError(error instanceof Error ? error.message : 'Sign out failed.'); }
  }

  if (!supabaseConfigured) {
    return <main className="fatal-state"><div className="brand-mark">B</div><h1>Configuration required</h1><p>Set <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> in your local environment, then restart the development server.</p><p className="muted">Use a public publishable key only. Never expose a service-role key in browser code.</p></main>;
  }
  if (checkingSession) return <main className="boot-state" aria-live="polite"><span className="spinner" />Loading Boardspace…</main>;
  if (user) return <WorkspacePage user={user} onSignOut={() => void handleSignOut()} globalError={authError} />;
  return <><AuthForm onAuthenticated={setUser} />{authError && <p className="global-auth-error" role="alert">{authError}</p>}</>;
}
