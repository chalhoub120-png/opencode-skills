import { describe, expect, it } from 'vitest';
import { canEdit, isWorkspaceRole, validateText } from './domain';

describe('workspace domain validation', () => {
  it('normalizes surrounding whitespace and respects the declared limit', () => {
    expect(validateText('  Release plan  ', 'Board title', 160)).toBe('Release plan');
    expect(() => validateText('x'.repeat(161), 'Board title', 160)).toThrow(/160 characters/);
  });

  it('rejects blank input', () => {
    expect(() => validateText(' \n ', 'Workspace name', 120)).toThrow(/required/);
  });

  it('recognizes only supported membership roles', () => {
    expect(isWorkspaceRole('owner')).toBe(true);
    expect(isWorkspaceRole('root')).toBe(false);
    expect(canEdit('viewer')).toBe(false);
    expect(canEdit('editor')).toBe(true);
  });
});
