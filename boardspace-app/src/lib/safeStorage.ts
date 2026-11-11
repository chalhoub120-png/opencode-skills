export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** Keeps authentication usable when browser storage is blocked or malformed. */
export function createSafeStorage(primary?: StorageLike): StorageLike {
  const fallback = new Map<string, string>();
  let primaryFailed = !primary;

  return {
    getItem(key) {
      if (!primaryFailed && primary) {
        try {
          const value = primary.getItem(key);
          if (value !== null) {
            if (key.endsWith('-auth-token')) {
              try {
                const parsed: unknown = JSON.parse(value);
                if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Invalid auth session.');
              } catch {
                try { primary.removeItem(key); } catch { primaryFailed = true; }
                fallback.delete(key);
                return null;
              }
            }
            return value;
          }
        } catch {
          primaryFailed = true;
        }
      }
      return fallback.get(key) ?? null;
    },
    setItem(key, value) {
      fallback.set(key, value);
      if (!primaryFailed && primary) {
        try { primary.setItem(key, value); }
        catch { primaryFailed = true; }
      }
    },
    removeItem(key) {
      fallback.delete(key);
      if (!primaryFailed && primary) {
        try { primary.removeItem(key); }
        catch { primaryFailed = true; }
      }
    },
  };
}
