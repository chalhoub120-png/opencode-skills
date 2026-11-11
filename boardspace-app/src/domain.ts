export type WorkspaceRole = 'owner' | 'admin' | 'editor' | 'viewer';

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
  created_by: string;
  role: WorkspaceRole;
}

export interface BoardCard {
  id: string;
  list_id: string;
  title: string;
  description: string;
  position: number;
  due_at: string | null;
  completed_at: string | null;
  revision: number;
}

export interface BoardList {
  id: string;
  title: string;
  position: number;
  is_archived: boolean;
  board_cards: BoardCard[];
}

export interface Board {
  id: string;
  title: string;
  position: number;
  revision: number;
  board_lists: BoardList[];
}

export interface WorkspaceBoardData {
  workspace: Workspace;
  boards: Board[];
}

export interface ServiceError {
  message: string;
  code?: string;
}

export function isWorkspaceRole(value: unknown): value is WorkspaceRole {
  return value === 'owner' || value === 'admin' || value === 'editor' || value === 'viewer';
}

export function canEdit(role: WorkspaceRole): boolean {
  return role !== 'viewer';
}

export function validateText(value: string, label: string, maxLength: number): string {
  const normalized = value.trim();
  if (!normalized) throw new Error(`${label} is required.`);
  if (normalized.length > maxLength) throw new Error(`${label} must be ${maxLength} characters or fewer.`);
  return normalized;
}
