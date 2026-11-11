/** Accepts only absolute HTTPS URLs suitable for opening as external links. */
export function validateExternalUrl(value: string): string | null {
  try {
    const url = new URL(value.trim());
    if (url.protocol !== 'https:' || !url.hostname || url.username || url.password) return null;
    return url.toString();
  } catch {
    return null;
  }
}
