import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import type { User } from '@supabase/supabase-js';
import type { Workspace } from '../../domain';
import { canEdit } from '../../domain';
import { listUserWorkspaces, createStarterWorkspace } from './workspaceRepository';
import { createBoard, createCard, createList, deleteBoard, listBoards, moveCard, setCardCompleted } from '../boards/boardRepository';
import { ExternalResources } from '../../components/ExternalResources';
import type { Board, BoardCard, BoardList } from '../../domain';
type Props = { user: User; onSignOut: () => void; globalError: string };

export function WorkspacePage({ user, onSignOut, globalError }: Props) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const workspaceRequest = useRef(0);

  const refresh = useCallback(async () => {
    const request = ++workspaceRequest.current;
    setLoading(true);
    setError('');
    try {
      const results = await listUserWorkspaces(user.id);
      if (request !== workspaceRequest.current) return;
      setWorkspaces(results);
      setWorkspaceId((current) => results.some((workspace) => workspace.id === current) ? current : results[0]?.id ?? '');
    } catch (reason) {
      if (request === workspaceRequest.current) setError(reason instanceof Error ? reason.message : 'Could not load your workspaces.');
    } finally {
      if (request === workspaceRequest.current) setLoading(false);
    }
  }, [user.id]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function createWorkspace() {
    const name = window.prompt('Name your workspace', 'Product team');
    if (name === null) return;
    setCreating(true);
    setError('');
    try {
      const newId = await createStarterWorkspace(name);
      await refresh();
      setWorkspaceId(newId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Workspace creation failed.');
    } finally {
      setCreating(false);
    }
  }

  const current = workspaces.find((workspace) => workspace.id === workspaceId) ?? null;

  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand-lockup" href="/" aria-label="Boardspace home"><span className="brand-mark">B</span> Boardspace</a>
        <div className="header-actions">
          <span className="signed-in-user">{user.email}</span>
          <button className="button button-quiet" onClick={onSignOut} type="button">Sign out</button>
        </div>
      </header>
      <div className="workspace-layout">
        <aside className="workspace-sidebar" aria-label="Workspace navigation">
          <div className="sidebar-heading"><span className="eyebrow">WORKSPACES</span><button className="icon-button" type="button" aria-label="Create workspace" onClick={() => void createWorkspace()} disabled={creating}>＋</button></div>
          {loading && <p className="muted">Loading workspaces…</p>}
          {!loading && workspaces.map((workspace) => (
            <button key={workspace.id} className={`workspace-nav-item ${workspace.id === workspaceId ? 'is-selected' : ''}`} onClick={() => setWorkspaceId(workspace.id)} type="button">
              <span className="workspace-glyph">{workspace.name.slice(0, 1).toUpperCase()}</span>
              <span className="workspace-nav-name">{workspace.name}</span>
              <span className="role-badge">{workspace.role}</span>
            </button>
          ))}
          {!loading && workspaces.length === 0 && <p className="sidebar-empty">Create a workspace to get started.</p>}
          <button className="sidebar-create" type="button" onClick={() => void createWorkspace()} disabled={creating}>＋ New workspace</button>
          <div className="sidebar-footer"><span className="status-dot" /> Secure workspace</div>
          <ExternalResources />
        </aside>
        <main className="main-content">
          {globalError && <div className="alert alert-error" role="alert">{globalError}</div>}
          {error && <div className="alert alert-error" role="alert"><span>{error}</span><button type="button" onClick={() => void refresh()}>Retry</button></div>}
          {loading ? <LoadingPanel /> : current ? <WorkspaceContent workspace={current} userId={user.id} onRefresh={refresh} /> : <WelcomePanel creating={creating} onCreate={createWorkspace} />}
        </main>
      </div>
    </div>
  );
}

function LoadingPanel() {
  return <section className="loading-panel" aria-live="polite"><span className="spinner" />Loading your workspace…</section>;
}

function WelcomePanel({ creating, onCreate }: { creating: boolean; onCreate: () => void }) {
  return <section className="welcome-panel"><div className="welcome-art" aria-hidden="true"><span>◫</span><span>✓</span><span>↗</span></div><p className="eyebrow">A BETTER WAY TO WORK</p><h1>Make room for great work.</h1><p>Create a workspace to organize projects, share boards with your team, and keep every next step visible.</p><button className="button button-primary" disabled={creating} onClick={onCreate} type="button">{creating ? 'Creating…' : 'Create your workspace'}</button></section>;
}

function WorkspaceContent({ workspace, userId, onRefresh }: { workspace: Workspace; userId: string; onRefresh: () => Promise<void> }) {
  const [boards, setBoards] = useState<Board[]>([]);
  const [boardId, setBoardId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const boardRequest = useRef(0);
  const canWrite = canEdit(workspace.role);

  const refreshBoards = useCallback(async () => {
    const request = ++boardRequest.current;
    setLoading(true);
    setError('');
    try {
      const result = await listBoards(workspace.id);
      if (request !== boardRequest.current) return;
      setBoards(result);
      setBoardId((current) => result.some((board) => board.id === current) ? current : result[0]?.id ?? '');
    } catch (reason) {
      if (request === boardRequest.current) setError(reason instanceof Error ? reason.message : 'Could not load boards.');
    } finally {
      if (request === boardRequest.current) setLoading(false);
    }
  }, [workspace.id]);
  useEffect(() => { void refreshBoards(); }, [refreshBoards]);
  const currentBoard = useMemo(() => boards.find((board) => board.id === boardId) ?? null, [boards, boardId]);

  async function addBoard() {
    if (!canWrite) return;
    const title = window.prompt('Board title', 'Untitled board');
    if (title === null) return;
    try {
      await createBoard(workspace.id, userId, title);
      await refreshBoards();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create board.'); }
  }

  async function removeBoard() {
    if (!currentBoard || workspace.role === 'viewer' || workspace.role === 'editor') return;
    if (!window.confirm(`Delete “${currentBoard.title}” and all its lists and cards? This cannot be undone.`)) return;
    try {
      await deleteBoard(workspace.id, currentBoard.id);
      await refreshBoards();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not delete board.'); }
  }

  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">{workspace.name.toUpperCase()} / PROJECT BOARD</p><h1>{currentBoard?.title ?? 'Your project boards'}</h1><p className="page-subtitle">Plan the next step, keep ownership clear, and move work forward.</p></div><div className="page-actions"><span className="role-pill">{workspace.role}</span>{canWrite && <button className="button button-primary" onClick={() => void addBoard()} type="button">＋ New board</button>}</div></div>
      <nav className="board-tabs" aria-label="Project boards">
        {boards.map((board) => <button key={board.id} aria-current={board.id === boardId ? 'page' : undefined} className={`board-tab ${board.id === boardId ? 'is-selected' : ''}`} onClick={() => setBoardId(board.id)} type="button">{board.title}</button>)}
        {boards.length === 0 && !loading && <span className="muted">No boards yet.</span>}
      </nav>
      {error && <div className="alert alert-error" role="alert"><span>{error}</span><button type="button" onClick={() => void refreshBoards()}>Retry</button></div>}
      {loading ? <LoadingPanel /> : currentBoard ? <BoardView board={currentBoard} workspace={workspace} canWrite={canWrite} onRefresh={refreshBoards} /> : <div className="empty-panel"><span className="empty-icon">▧</span><h2>Your first board starts here</h2><p>Boards turn a project into clear lists and manageable work.</p>{canWrite && <button className="button button-primary" onClick={() => void addBoard()} type="button">Create a board</button>}</div>}
      {currentBoard && (workspace.role === 'owner' || workspace.role === 'admin') && <div className="danger-zone"><button className="text-button danger-text" type="button" onClick={() => void removeBoard()}>Delete board</button></div>}
      <button className="refresh-link" type="button" onClick={() => { void onRefresh(); }}>Refresh workspace</button>
    </>
  );
}

function BoardView({ board, workspace, canWrite, onRefresh }: { board: Board; workspace: Workspace; canWrite: boolean; onRefresh: () => Promise<void> }) {
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const lists = board.board_lists.filter((list) => !list.is_archived);

  async function addList() {
    if (!canWrite) return;
    const title = window.prompt('List name', 'New list');
    if (title === null) return;
    setBusyId('list'); setError('');
    try { await createList(workspace.id, board.id, title, lists); await onRefresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create list.'); }
    finally { setBusyId(''); }
  }

  async function handleCardAction(action: () => Promise<void>): Promise<boolean> {
    if (busyId) return false;
    setBusyId('content');
    setError('');
    try {
      await action();
      await onRefresh();
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The change could not be saved.');
      return false;
    } finally {
      setBusyId('');
    }
  }

  return (
    <section className="board-area" aria-label={`${board.title} board`}>
      {error && <div className="alert alert-error board-alert" role="alert">{error}</div>}
      <div className="kanban-scroll">
        {lists.map((list) => <BoardColumn key={list.id} list={list} lists={lists} workspace={workspace} canWrite={canWrite} busy={busyId === 'content'} onCardAction={handleCardAction} />)}
        {canWrite && <button className="add-list-tile" disabled={busyId === 'list'} onClick={() => void addList()} type="button">＋ <span>{busyId === 'list' ? 'Adding…' : 'Add a list'}</span></button>}
        {!canWrite && lists.length === 0 && <p className="muted">No active lists in this board.</p>}
      </div>
    </section>
  );
}

function BoardColumn({ list, lists, workspace, canWrite, busy, onCardAction }: { list: BoardList; lists: BoardList[]; workspace: Workspace; canWrite: boolean; busy: boolean; onCardAction: (action: () => Promise<void>) => Promise<boolean> }) {
  const [title, setTitle] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    const saved = await onCardAction(() => createCard(workspace.id, list.id, title));
    if (saved) setTitle('');
  }
  return (
    <section className="kanban-column" aria-label={`${list.title} list`}>
      <header className="column-heading"><h2>{list.title}</h2><span className="count-chip">{list.board_cards.length}</span></header>
      <div className="column-cards">
        {list.board_cards.map((card) => <article key={card.id} className={`task-card ${card.completed_at ? 'is-done' : ''}`}>
          <div className="task-topline"><span className="task-dot" /><span className="task-id">{card.id.slice(0, 6).toUpperCase()}</span></div>
          <h3>{card.title}</h3>
          {card.description && <p>{card.description}</p>}
          {card.due_at && <time dateTime={card.due_at} className="due-date">Due {new Date(`${card.due_at}T00:00:00`).toLocaleDateString()}</time>}
          {canWrite && <div className="task-actions"><label className="complete-label"><input type="checkbox" checked={Boolean(card.completed_at)} onChange={(event) => void onCardAction(() => setCardCompleted(workspace.id, card, event.target.checked))} /><span>{card.completed_at ? 'Completed' : 'Mark complete'}</span></label><label className="move-control"><span className="sr-only">Move {card.title} to list</span><select aria-label={`Move ${card.title} to list`} value={list.id} onChange={(event) => void onCardAction(() => moveCard(workspace.id, card, event.target.value, lists))}><option value={list.id}>Move…</option>{lists.filter((candidate) => candidate.id !== list.id).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.title}</option>)}</select></label></div>}
        </article>)}
        {list.board_cards.length === 0 && <p className="column-empty">No cards here yet.</p>}
      </div>
      {canWrite && <form className="add-card-form" onSubmit={(event) => void submit(event)}><input aria-label={`New card in ${list.title}`} maxLength={200} placeholder="Add a card…" value={title} onChange={(event) => setTitle(event.target.value)} /><button aria-label="Add card" disabled={busy || !title.trim()} type="submit">＋</button></form>}
    </section>
  );
}
