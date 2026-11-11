import { useState, type FormEvent } from 'react';
import type { User } from '@supabase/supabase-js';
import { signIn, signUp } from './authService';
import { ExternalResources } from '../../components/ExternalResources';

type Props = { onAuthenticated: (user: User) => void };

export function AuthForm({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      if (mode === 'sign-in') {
        const user = await signIn(email, password);
        onAuthenticated(user);
      } else {
        await signUp(email, password);
        setMessage('Account created. Check your email to confirm your address, then sign in.');
        setMode('sign-in');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication failed. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <a className="brand-lockup" href="/" aria-label="Boardspace home"><span className="brand-mark">B</span> Boardspace</a>
        <p className="eyebrow">YOUR TEAM, IN SYNC</p>
        <h1 id="auth-title">{mode === 'sign-in' ? 'Welcome back' : 'Create your account'}</h1>
        <p className="auth-subtitle">A clear place to plan work and move it forward.</p>
        <form onSubmit={submit} className="auth-form">
          <label htmlFor="email">Work email</label>
          <input id="email" type="email" autoComplete="email" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'} required minLength={10} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} />
          <p className="field-hint">Use 10–128 characters.</p>
          {error && <p className="notice notice-error" role="alert">{error}</p>}
          {message && <p className="notice notice-success" role="status">{message}</p>}
          <button className="button button-primary button-wide" disabled={busy} type="submit">{busy ? 'Please wait…' : mode === 'sign-in' ? 'Sign in' : 'Create account'}</button>
        </form>
        <p className="auth-switch">{mode === 'sign-in' ? 'New to Boardspace?' : 'Already have an account?'}{' '}
          <button type="button" className="text-button" onClick={() => { setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in'); setError(''); setMessage(''); }}>
            {mode === 'sign-in' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
        <p className="privacy-note">Your workspace data is protected by workspace membership policies.</p>
        <ExternalResources />
      </section>
    </main>
  );
}
