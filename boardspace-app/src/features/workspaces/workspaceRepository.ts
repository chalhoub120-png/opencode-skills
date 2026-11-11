import { isWorkspaceRole, validateText, type Workspace, type WorkspaceRole } from '../../domain';
import { supabase } from '../../lib/supabase';

function client() {
  if (!supabase) throw new Error('Cloud client is not configured.');
  return supabase;
}

export async function listUserWorkspaces(userId: string): Promise<Workspace[]> {
  const db = client();
  const { data: memberships, error: membershipError } = await db
    .from('workspace_members')
    .select('workspace_id,role')
    .eq('user_id', userId);
  if (membershipError) throw new Error('Could not load workspace memberships.');
  if (!memberships?.length) return [];

  const { data, error } = await db
    .from('workspaces')
    .select('id,name,created_by,created_at')
    .in('id', memberships.map((entry) => entry.workspace_id))
    .order('created_at', { ascending: true });
  if (error) throw new Error('Could not load workspaces.');

  const roleByWorkspace = new Map<string, WorkspaceRole>();
  memberships.forEach((entry) => {
    if (isWorkspaceRole(entry.role)) roleByWorkspace.set(entry.workspace_id, entry.role);
  });
  return (data ?? []).flatMap((workspace) => {
    const role = roleByWorkspace.get(workspace.id);
    return role ? [{ ...workspace, role }] : [];
  });
}

export async function createStarterWorkspace(name: string): Promise<string> {
  const safeName = validateText(name, 'Workspace name', 120);
  const { data, error } = await client().rpc('create_workspace_with_starter', { p_name: safeName });
  if (error) throw new Error('Could not create the starter workspace. Check your connection and permissions.');
  if (typeof data !== 'string') throw new Error('Workspace creation returned an invalid identifier.');
  return data;
}
