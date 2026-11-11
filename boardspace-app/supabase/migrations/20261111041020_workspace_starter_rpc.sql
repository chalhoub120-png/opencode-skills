
create or replace function public.create_workspace_with_starter(p_name text)
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_workspace_id uuid;
  v_board_id uuid;
  v_todo_id uuid;
  v_progress_id uuid;
  v_done_id uuid;
begin
  if (select auth.uid()) is null then
    raise exception 'Authentication required' using errcode = '28000';
  end if;
  if p_name is null or length(btrim(p_name)) not between 1 and 120 then
    raise exception 'Workspace name must be between 1 and 120 characters' using errcode = '22023';
  end if;

  insert into public.workspaces(name, created_by)
  values (btrim(p_name), (select auth.uid()))
  returning id into v_workspace_id;

  insert into public.boards(workspace_id, title, position, created_by)
  values (v_workspace_id, 'Product launch', 0, (select auth.uid()))
  returning id into v_board_id;

  insert into public.board_lists(workspace_id, board_id, title, position)
  values (v_workspace_id, v_board_id, 'To do', 0) returning id into v_todo_id;
  insert into public.board_lists(workspace_id, board_id, title, position)
  values (v_workspace_id, v_board_id, 'In progress', 1) returning id into v_progress_id;
  insert into public.board_lists(workspace_id, board_id, title, position)
  values (v_workspace_id, v_board_id, 'Done', 2) returning id into v_done_id;

  insert into public.board_cards(workspace_id, list_id, title, description, position, created_by) values
    (v_workspace_id, v_todo_id, 'Define the first milestone', 'Write down the smallest outcome that proves the project is moving forward.', 0, (select auth.uid())),
    (v_workspace_id, v_todo_id, 'Collect feedback from the team', 'Capture open questions and assign a clear next step.', 1, (select auth.uid())),
    (v_workspace_id, v_progress_id, 'Set up the project workspace', 'Agree on ownership, due dates, and the team communication rhythm.', 0, (select auth.uid())),
    (v_workspace_id, v_done_id, 'Create the project plan', 'The initial scope and delivery milestones are ready.', 0, (select auth.uid()));

  return v_workspace_id;
end;
$$;

revoke all on function public.create_workspace_with_starter(text) from public, anon;
grant execute on function public.create_workspace_with_starter(text) to authenticated;
