-- Optimistic concurrency prevents one browser/device silently overwriting another.
alter table public.boardspace_state
  add column if not exists revision integer not null default 1;

create or replace function public.save_boardspace_state(p_state jsonb, p_expected_revision integer)
returns table(saved boolean, current_revision integer)
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_revision integer;
begin
  if auth.uid() is null then
    raise exception 'Authentication required' using errcode = '28000';
  end if;
  if p_expected_revision is null or p_expected_revision < 0 then
    raise exception 'Invalid expected revision' using errcode = '22023';
  end if;
  if p_state is null or jsonb_typeof(p_state) is distinct from 'object' or pg_column_size(p_state) > 2097152 then
    raise exception 'Invalid or oversized board state' using errcode = '22023';
  end if;

  if p_expected_revision = 0 then
    insert into public.boardspace_state(user_id, state, revision)
    values (auth.uid(), p_state, 1)
    on conflict (user_id) do nothing
    returning revision into v_revision;
    if found then
      return query select true, v_revision;
      return;
    end if;
  else
    update public.boardspace_state as b
      set state = p_state, revision = b.revision + 1, updated_at = now()
      where b.user_id = auth.uid() and b.revision = p_expected_revision
      returning b.revision into v_revision;
    if found then
      return query select true, v_revision;
      return;
    end if;
  end if;

  select b.revision into v_revision
    from public.boardspace_state as b
    where b.user_id = auth.uid();
  return query select false, coalesce(v_revision, 0);
end;
$$;

revoke all on function public.save_boardspace_state(jsonb, integer) from public, anon;
grant execute on function public.save_boardspace_state(jsonb, integer) to authenticated;
