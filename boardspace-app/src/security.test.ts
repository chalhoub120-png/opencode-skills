import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ExternalResources } from './components/ExternalResources';
import { createSafeStorage, type StorageLike } from './lib/safeStorage';
import { validateExternalUrl } from './lib/safeUrl';

describe('resilient session storage', () => {
  it('falls back to in-memory storage when browser storage is unavailable', () => {
    const storage = createSafeStorage();
    storage.setItem('session', 'value');
    expect(storage.getItem('session')).toBe('value');
    storage.removeItem('session');
    expect(storage.getItem('session')).toBeNull();
  });

  it('falls back when browser storage access throws', () => {
    const blocked: StorageLike = {
      getItem: () => { throw new Error('blocked'); },
      setItem: () => { throw new Error('blocked'); },
      removeItem: () => { throw new Error('blocked'); },
    };
    const storage = createSafeStorage(blocked);
    storage.setItem('session', 'value');
    expect(storage.getItem('session')).toBe('value');
  });

  it('discards malformed Supabase auth-session JSON but preserves normal values', () => {
    const values = new Map([['sb-demo-auth-token', '{broken'], ['sb-demo-code-verifier', 'plain-verifier']]);
    const primary: StorageLike = {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => { values.set(key, value); },
      removeItem: (key) => { values.delete(key); },
    };
    const storage = createSafeStorage(primary);
    expect(storage.getItem('sb-demo-auth-token')).toBeNull();
    expect(values.has('sb-demo-auth-token')).toBe(false);
    expect(storage.getItem('sb-demo-code-verifier')).toBe('plain-verifier');
  });
});

describe('untrusted text and external URLs', () => {
  it('renders HTML-like search input as escaped text, never as markup', () => {
    const hostile = '<img src=x onerror=alert(1)>';
    const html = renderToStaticMarkup(createElement('span', null, hostile));
    expect(html).toContain('&lt;img');
    expect(html).not.toContain('<img');
    expect(html).not.toMatch(/<img\b/i);
    expect(html.match(/<span>/g)).toHaveLength(1);
  });

  it('renders external resource links with HTTPS and opener protections', () => {
    const html = renderToStaticMarkup(createElement(ExternalResources));
    expect(html.match(/target="_blank"/g)).toHaveLength(2);
    expect(html.match(/rel="noopener noreferrer"/g)).toHaveLength(2);
    expect(html).toContain('https://supabase.com/docs');
    expect(html).toContain('https://react.dev/learn');
  });

  it('allows absolute HTTPS URLs and rejects unsafe or ambiguous schemes', () => {
    expect(validateExternalUrl('https://example.com/path')).toBe('https://example.com/path');
    for (const value of ['javascript:alert(1)', 'data:text/html,hello', '//example.com', 'http://example.com', 'https://user:pass@example.com']) {
      expect(validateExternalUrl(value)).toBeNull();
    }
  });
});
