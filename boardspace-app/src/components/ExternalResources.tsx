import { validateExternalUrl } from '../lib/safeUrl';

const resources = [
  { label: 'Supabase docs', url: 'https://supabase.com/docs' },
  { label: 'React docs', url: 'https://react.dev/learn' },
] as const;

export function ExternalResources() {
  return (
    <nav className="external-resources" aria-label="External resources">
      {resources.map(({ label, url }) => {
        const safeUrl = validateExternalUrl(url);
        return safeUrl ? <a key={label} href={safeUrl} target="_blank" rel="noopener noreferrer">{label}</a> : null;
      })}
    </nav>
  );
}
