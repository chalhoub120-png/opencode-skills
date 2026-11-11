import type { Board, BoardCard, BoardList } from '../../domain';
import { validateText } from '../../domain';
import { supabase } from '../../lib/supabase';

function client() {
  if (!supabase) throw new Error('Cloud client is not configured.');
  return supabase;
}

function rethrow(message: string, error: { message?: string } | null): never {
  console.error(message, error);
  throw new Error(message);
}

export async function listBoards(workspaceId: string): Promise<Board[]> {
  const { data, error } = await client()
    .from('boards')
    .select('id,title,position,revision,board_lists(id,title,position,is_archived,board_cards(id,list_id,title,description,position,due_at,completed_at,revision))')
    .eq('workspace_id', workspaceId)
    .order('position', { ascending: true });
  if (error) rethrow('Could not load boards.', error);
  return (data ?? []).map((board) => ({
    ...board,
    board_lists: [...(board.board_lists ?? [])]
      .sort((a, b) => Number(a.position) - Number(b.position))
      .map((list) => ({
        ...list,
        board_cards: [...(list.board_cards ?? [])].sort((a, b) => Number(a.position) - Number(b.position)),
      })),
  })) as Board[];
}

export async function createBoard(workspaceId: string, userId: string, title: string): Promise<void> {
  const safeTitle = validateText(title, 'Board title', 160);
  const { data: existing, error: readError } = await client()
    .from('boards').select('position').eq('workspace_id', workspaceId).order('position', { ascending: false }).limit(1);
  if (readError) rethrow('Could not determine board ordering.', readError);
  const position = Number(existing?.[0]?.position ?? -1) + 1;
  const { error } = await client().from('boards').insert({ workspace_id: workspaceId, created_by: userId, title: safeTitle, position });
  if (error) rethrow('Could not create the board.', error);
}

export async function createList(workspaceId: string, boardId: string, title: string, currentLists: BoardList[]): Promise<void> {
  const safeTitle = validateText(title, 'List title', 120);
  const position = currentLists.reduce((max, list) => Math.max(max, Number(list.position)), -1) + 1;
  const { error } = await client().from('board_lists').insert({ workspace_id: workspaceId, board_id: boardId, title: safeTitle, position });
  if (error) rethrow('Could not create the list.', error);
}

export async function createCard(workspaceId: string, listId: string, title: string): Promise<void> {
  const safeTitle = validateText(title, 'Card title', 200);
  const { data: existing, error: readError } = await client()
    .from('board_cards').select('position').eq('workspace_id', workspaceId).eq('list_id', listId).order('position', { ascending: false }).limit(1);
  if (readError) rethrow('Could not determine card ordering.', readError);
  const position = Number(existing?.[0]?.position ?? -1) + 1;
  const { error } = await client().from('board_cards').insert({ workspace_id: workspaceId, list_id: listId, title: safeTitle, position });
  if (error) rethrow('Could not create the card.', error);
}

export async function setCardCompleted(workspaceId: string, card: BoardCard, completed: boolean): Promise<void> {
  const { data, error } = await client().from('board_cards')
    .update({ completed_at: completed ? new Date().toISOString() : null, revision: card.revision + 1 })
    .eq('workspace_id', workspaceId)
    .eq('id', card.id)
    .eq('revision', card.revision)
    .select('id')
    .maybeSingle();
  if (error) rethrow('Could not update the card.', error);
  if (!data) throw new Error('This card changed in another session. Refresh before trying again.');
}

export async function moveCard(workspaceId: string, card: BoardCard, targetListId: string, lists: BoardList[]): Promise<void> {
  const targetList = lists.find((list) => list.id === targetListId);
  if (!targetList || targetListId === card.list_id) throw new Error('Choose a different destination list.');
  const position = targetList.board_cards.reduce((max, candidate) => Math.max(max, Number(candidate.position)), -1) + 1;
  const { data, error } = await client().from('board_cards')
    .update({ list_id: targetListId, position, revision: card.revision + 1 })
    .eq('workspace_id', workspaceId)
    .eq('id', card.id)
    .eq('revision', card.revision)
    .select('id')
    .maybeSingle();
  if (error) rethrow('Could not move the card.', error);
  if (!data) throw new Error('This card changed in another session. Refresh before moving it.');
}

export async function deleteBoard(workspaceId: string, boardId: string): Promise<void> {
  const { error } = await client().from('boards').delete().eq('workspace_id', workspaceId).eq('id', boardId);
  if (error) rethrow('Could not delete the board.', error);
}
