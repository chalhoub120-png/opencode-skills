-- One private state document per authenticated user. RLS is the authorization boundary.
create table if not exists public.boardspace_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null,
  updated_at timestamptz not null default now(),
  constraint boardspace_state_size check (pg_column_size(state) <= 2097152)
);

alter table public.boardspace_state enable row level security;
alter table public.boardspace_state force row level security;
revoke all on public.boardspace_state from anon;
grant select, insert, update, delete on public.boardspace_state to authenticated;

drop policy if exists "Users manage only their own board state" on public.boardspace_state;
create policy "Users manage only their own board state"
  on public.boardspace_state
  for all
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create or replace function public.set_boardspace_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists boardspace_state_updated_at on public.boardspace_state;
create trigger boardspace_state_updated_at
  before update on public.boardspace_state
  for each row execute function public.set_boardspace_updated_at();
