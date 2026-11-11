-- Additive normalized schema; legacy Boardspace state is preserved until a reviewed backfill.
create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(btrim(name)) between 1 and 120),
  created_by uuid not null default auth.uid() references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','admin','editor','viewer')),
  joined_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

create table if not exists public.boards (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null check (length(btrim(title)) between 1 and 160),
  position numeric not null default 0 check (position >= 0),
  created_by uuid not null default auth.uid() references auth.users(id) on delete restrict,
  revision bigint not null default 1 check (revision > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, id)
);

create table if not exists public.board_lists (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  board_id uuid not null,
  title text not null check (length(btrim(title)) between 1 and 120),
  position numeric not null default 0 check (position >= 0),
  is_archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, id),
  foreign key (workspace_id, board_id) references public.boards(workspace_id, id) on delete cascade
);

create table if not exists public.board_cards (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  list_id uuid not null,
  title text not null check (length(btrim(title)) between 1 and 200),
  description text not null default '' check (length(description) <= 8000),
  position numeric not null default 0 check (position >= 0),
  due_at date,
  completed_at timestamptz,
  archived_at timestamptz,
  created_by uuid not null default auth.uid() references auth.users(id) on delete restrict,
  revision bigint not null default 1 check (revision > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, id),
  foreign key (workspace_id, list_id) references public.board_lists(workspace_id, id) on delete cascade
);

create table if not exists public.labels (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null check (length(btrim(name)) between 1 and 60),
  color text not null default '#6558d3' check (color ~ '^#[0-9A-Fa-f]{6}$'),
  unique (workspace_id, id),
  unique (workspace_id, name)
);

create table if not exists public.card_labels (
  workspace_id uuid not null,
  card_id uuid not null,
  label_id uuid not null,
  primary key (card_id, label_id),
  foreign key (workspace_id, card_id) references public.board_cards(workspace_id, id) on delete cascade,
  foreign key (workspace_id, label_id) references public.labels(workspace_id, id) on delete cascade
);

create table if not exists public.card_assignees (
  workspace_id uuid not null,
  card_id uuid not null,
  user_id uuid not null,
  assigned_at timestamptz not null default now(),
  primary key (card_id, user_id),
  foreign key (workspace_id, card_id) references public.board_cards(workspace_id, id) on delete cascade,
  foreign key (workspace_id, user_id) references public.workspace_members(workspace_id, user_id) on delete cascade
);

create table if not exists public.card_comments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  card_id uuid not null,
  author_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  body text not null check (length(btrim(body)) between 1 and 4000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (workspace_id, card_id) references public.board_cards(workspace_id, id) on delete cascade
);

create table if not exists public.card_checklists (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  card_id uuid not null,
  title text not null check (length(btrim(title)) between 1 and 120),
  position numeric not null default 0 check (position >= 0),
  unique (workspace_id, id),
  foreign key (workspace_id, card_id) references public.board_cards(workspace_id, id) on delete cascade
);

create table if not exists public.checklist_items (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  checklist_id uuid not null,
  title text not null check (length(btrim(title)) between 1 and 300),
  is_done boolean not null default false,
  position numeric not null default 0 check (position >= 0),
  foreign key (workspace_id, checklist_id) references public.card_checklists(workspace_id, id) on delete cascade
);

create table if not exists public.activity_events (
  id bigint generated always as identity primary key,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  actor_id uuid default auth.uid() references auth.users(id) on delete set null,
  entity_type text not null check (entity_type in ('board','list','card','comment')),
  entity_id uuid not null,
  event_type text not null check (length(event_type) between 1 and 64),
  payload jsonb not null default '{}'::jsonb check (pg_column_size(payload) <= 16384),
  created_at timestamptz not null default now()
);

create or replace function public.is_workspace_member(p_workspace_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.workspace_members wm where wm.workspace_id = p_workspace_id and wm.user_id = (select auth.uid()));
$$;

create or replace function public.has_workspace_role(p_workspace_id uuid, p_roles text[])
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.workspace_members wm where wm.workspace_id = p_workspace_id and wm.user_id = (select auth.uid()) and wm.role = any(p_roles));
$$;

revoke all on function public.is_workspace_member(uuid) from public, anon;
revoke all on function public.has_workspace_role(uuid, text[]) from public, anon;
grant execute on function public.is_workspace_member(uuid) to authenticated;
grant execute on function public.has_workspace_role(uuid, text[]) to authenticated;

create or replace function public.add_workspace_owner()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.workspace_members(workspace_id, user_id, role) values (new.id, new.created_by, 'owner');
  return new;
end;
$$;
revoke all on function public.add_workspace_owner() from public, anon, authenticated;
drop trigger if exists workspaces_add_owner on public.workspaces;
create trigger workspaces_add_owner after insert on public.workspaces for each row execute function public.add_workspace_owner();

create or replace function public.touch_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end;
$$;
revoke all on function public.touch_updated_at() from public, anon, authenticated;
do $$
declare t text;
begin
  foreach t in array array['workspaces','boards','board_lists','board_cards','card_comments'] loop
    execute format('drop trigger if exists touch_updated_at on public.%I', t);
    execute format('create trigger touch_updated_at before update on public.%I for each row execute function public.touch_updated_at()', t);
  end loop;
end $$;

do $$
declare t text;
begin
  foreach t in array array['workspaces','workspace_members','boards','board_lists','board_cards','labels','card_labels','card_assignees','card_comments','card_checklists','checklist_items','activity_events'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('grant select, insert, update, delete on public.%I to authenticated', t);
  end loop;
end $$;

-- Workspace membership is the authorization boundary.
drop policy if exists workspace_member_read on public.workspaces;
create policy workspace_member_read on public.workspaces for select to authenticated using (public.is_workspace_member(id));
drop policy if exists workspace_create on public.workspaces;
create policy workspace_create on public.workspaces for insert to authenticated with check (created_by = (select auth.uid()));
drop policy if exists workspace_owner_update on public.workspaces;
create policy workspace_owner_update on public.workspaces for update to authenticated using (public.has_workspace_role(id, array['owner','admin'])) with check (public.has_workspace_role(id, array['owner','admin']));
drop policy if exists workspace_owner_delete on public.workspaces;
create policy workspace_owner_delete on public.workspaces for delete to authenticated using (public.has_workspace_role(id, array['owner']));

drop policy if exists workspace_member_read on public.workspace_members;
create policy workspace_member_read on public.workspace_members for select to authenticated using (user_id = (select auth.uid()) or public.has_workspace_role(workspace_id, array['owner','admin']));
-- Membership INSERT/UPDATE/DELETE is withheld until a trusted invitation and last-owner flow exists.

drop policy if exists boards_read on public.boards;
create policy boards_read on public.boards for select to authenticated using (public.is_workspace_member(workspace_id));
drop policy if exists boards_create on public.boards;
create policy boards_create on public.boards for insert to authenticated with check (public.has_workspace_role(workspace_id, array['owner','admin','editor']) and created_by = (select auth.uid()));
drop policy if exists boards_update on public.boards;
create policy boards_update on public.boards for update to authenticated using (public.has_workspace_role(workspace_id, array['owner','admin','editor'])) with check (public.has_workspace_role(workspace_id, array['owner','admin','editor']));
drop policy if exists boards_delete on public.boards;
create policy boards_delete on public.boards for delete to authenticated using (public.has_workspace_role(workspace_id, array['owner','admin']));

-- Editors and higher can manage board content; viewers can read only.
do $$
declare t text;
begin
  foreach t in array array['board_lists','board_cards','labels','card_labels','card_assignees','card_checklists','checklist_items'] loop
    execute format('drop policy if exists workspace_read on public.%I', t);
    execute format('create policy workspace_read on public.%I for select to authenticated using (public.is_workspace_member(workspace_id))', t);
    execute format('drop policy if exists workspace_insert on public.%I', t);
    execute format('create policy workspace_insert on public.%I for insert to authenticated with check (public.has_workspace_role(workspace_id, array[''owner'',''admin'',''editor'']))', t);
    execute format('drop policy if exists workspace_update on public.%I', t);
    execute format('create policy workspace_update on public.%I for update to authenticated using (public.has_workspace_role(workspace_id, array[''owner'',''admin'',''editor''])) with check (public.has_workspace_role(workspace_id, array[''owner'',''admin'',''editor'']))', t);
    execute format('drop policy if exists workspace_delete on public.%I', t);
    execute format('create policy workspace_delete on public.%I for delete to authenticated using (public.has_workspace_role(workspace_id, array[''owner'',''admin'',''editor'']))', t);
  end loop;
end $$;

drop policy if exists comments_read on public.card_comments;
create policy comments_read on public.card_comments for select to authenticated using (public.is_workspace_member(workspace_id));
drop policy if exists comments_insert on public.card_comments;
create policy comments_insert on public.card_comments for insert to authenticated with check (public.is_workspace_member(workspace_id) and author_id = (select auth.uid()));
drop policy if exists comments_update on public.card_comments;
create policy comments_update on public.card_comments for update to authenticated using (author_id = (select auth.uid()) and public.is_workspace_member(workspace_id)) with check (author_id = (select auth.uid()) and public.is_workspace_member(workspace_id));
drop policy if exists comments_delete on public.card_comments;
create policy comments_delete on public.card_comments for delete to authenticated using (author_id = (select auth.uid()) or public.has_workspace_role(workspace_id, array['owner','admin']));

drop policy if exists activity_read on public.activity_events;
create policy activity_read on public.activity_events for select to authenticated using (public.is_workspace_member(workspace_id));
-- No client mutation policy for the audit log.

create index if not exists boards_workspace_position_idx on public.boards(workspace_id, position);
create index if not exists board_lists_board_position_idx on public.board_lists(board_id, position);
create index if not exists board_cards_list_position_idx on public.board_cards(list_id, position);
create index if not exists board_cards_workspace_updated_idx on public.board_cards(workspace_id, updated_at desc);
create index if not exists card_comments_card_created_idx on public.card_comments(card_id, created_at);
create index if not exists activity_workspace_created_idx on public.activity_events(workspace_id, created_at desc);
