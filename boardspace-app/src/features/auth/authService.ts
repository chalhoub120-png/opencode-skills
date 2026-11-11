import type { AuthError, Session, User } from '@supabase/supabase-js';
import { supabase } from '../../lib/supabase';

function requireClient() {
  if (!supabase) throw new Error('Cloud configuration is missing. Add the required VITE_SUPABASE variables.');
  return supabase;
}

function throwAuthError(error: AuthError | null): void {
  if (error) throw new Error(error.message || 'Authentication failed.');
}

export async function getCurrentSession(): Promise<Session | null> {
  const { data, error } = await requireClient().auth.getSession();
  throwAuthError(error);
  return data.session;
}

export async function signIn(email: string, password: string): Promise<User> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) throw new Error('Enter a valid email address.');
  if (password.length < 10 || password.length > 128) throw new Error('Password must contain 10–128 characters.');
  const { data, error } = await requireClient().auth.signInWithPassword({ email: normalizedEmail, password });
  throwAuthError(error);
  if (!data.user) throw new Error('Sign in did not return a user.');
  return data.user;
}

export async function signUp(email: string, password: string): Promise<void> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) throw new Error('Enter a valid email address.');
  if (password.length < 10 || password.length > 128) throw new Error('Password must contain 10–128 characters.');
  const { error } = await requireClient().auth.signUp({
    email: normalizedEmail,
    password,
    options: { emailRedirectTo: window.location.origin },
  });
  throwAuthError(error);
}

export async function signOut(): Promise<void> {
  const { error } = await requireClient().auth.signOut();
  throwAuthError(error);
}
