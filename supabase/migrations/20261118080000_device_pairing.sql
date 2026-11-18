-- ULTRON device pairing control plane. Apply only after explicit production approval.
create table if not exists public.ultron_devices (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  device_name text not null check (char_length(device_name) between 1 and 80),
  platform text not null check (platform in ('windows','macos','linux','ios','ipados','android','other')),
  capabilities jsonb not null default '{}'::jsonb,
  token_hash text not null unique check (token_hash ~ '^[a-f0-9]{64}$'),
  status text not null default 'paired' check (status in ('paired','revoked')),
  paired_at timestamptz not null default now(),
  last_seen_at timestamptz,
  revoked_at timestamptz
);
create table if not exists public.ultron_pairing_challenges (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  code_hash text not null check (code_hash ~ '^[a-f0-9]{64}$'),
  attempts smallint not null default 0 check (attempts between 0 and 5),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  consumed_at timestamptz,
  check (expires_at > created_at)
);
create index if not exists ultron_devices_owner_idx on public.ultron_devices(owner_id, paired_at desc);
create index if not exists ultron_pairing_challenges_expiry_idx on public.ultron_pairing_challenges(expires_at);
alter table public.ultron_devices enable row level security;
alter table public.ultron_pairing_challenges enable row level security;
revoke all on public.ultron_devices, public.ultron_pairing_challenges from anon, authenticated;
grant all on public.ultron_devices, public.ultron_pairing_challenges to service_role;

create or replace function public.consume_ultron_pairing_challenge(
  p_challenge_id uuid, p_code_hash text, p_device_name text, p_platform text,
  p_capabilities jsonb, p_token_hash text
) returns uuid
language plpgsql security invoker set search_path = ''
as $$
declare
  v_challenge public.ultron_pairing_challenges%rowtype;
  v_device_id uuid;
begin
  if coalesce(
       nullif(pg_catalog.current_setting('request.jwt.claim.role', true), ''),
       (nullif(pg_catalog.current_setting('request.jwt.claims', true), '')::jsonb ->> 'role'),
       ''
     ) <> 'service_role' then raise exception 'service role required'; end if;
  if p_challenge_id is null or p_code_hash is null or p_token_hash is null or p_code_hash !~ '^[a-f0-9]{64}$'
     or p_token_hash !~ '^[a-f0-9]{64}$'
     or nullif(pg_catalog.btrim(p_device_name), '') is null
     or pg_catalog.char_length(p_device_name) > 80
     or p_platform is null or p_platform not in ('windows','macos','linux','ios','ipados','android','other')
     or pg_catalog.jsonb_typeof(coalesce(p_capabilities, '{}'::jsonb)) <> 'object'
     or pg_catalog.octet_length(coalesce(p_capabilities, '{}'::jsonb)::text) > 4096 then
    raise exception 'invalid pairing request';
  end if;
  select * into v_challenge from public.ultron_pairing_challenges
    where id = p_challenge_id for update;
  if not found or v_challenge.consumed_at is not null
     or v_challenge.expires_at <= pg_catalog.now()
     or v_challenge.attempts >= 5 then return null; end if;
  update public.ultron_pairing_challenges set attempts = attempts + 1 where id = p_challenge_id;
  if v_challenge.code_hash <> p_code_hash then return null; end if;
  update public.ultron_pairing_challenges set consumed_at = pg_catalog.now()
    where id = p_challenge_id and consumed_at is null;
  insert into public.ultron_devices(owner_id, device_name, platform, capabilities, token_hash)
  values (v_challenge.owner_id, pg_catalog.left(pg_catalog.btrim(p_device_name), 80),
          p_platform, coalesce(p_capabilities, '{}'::jsonb), p_token_hash)
  returning id into v_device_id;
  return v_device_id;
end;
$$;
revoke all on function public.consume_ultron_pairing_challenge(uuid,text,text,text,jsonb,text) from public, anon, authenticated;
grant execute on function public.consume_ultron_pairing_challenge(uuid,text,text,text,jsonb,text) to service_role;


-- Per-IP pairing endpoint rate limits. The key is a SHA-256 hash of the
-- Cloudflare-provided client IP and endpoint label; raw IP addresses are not stored.
create table if not exists public.ultron_pairing_rate_limits (
  key_hash text primary key check (key_hash ~ '^[a-f0-9]{64}$'),
  window_started_at timestamptz not null,
  request_count integer not null check (request_count >= 1),
  updated_at timestamptz not null default now()
);
alter table public.ultron_pairing_rate_limits enable row level security;
revoke all on public.ultron_pairing_rate_limits from anon, authenticated;
grant all on public.ultron_pairing_rate_limits to service_role;

create or replace function public.consume_ultron_pairing_rate_limit(
  p_key_hash text, p_limit integer, p_window_seconds integer
) returns boolean
language plpgsql security invoker set search_path = ''
as $$
declare
  v_count integer;
begin
  if coalesce(
       nullif(pg_catalog.current_setting('request.jwt.claim.role', true), ''),
       (nullif(pg_catalog.current_setting('request.jwt.claims', true), '')::jsonb ->> 'role'),
       ''
     ) <> 'service_role' then raise exception 'service role required'; end if;
  if p_key_hash is null or p_key_hash !~ '^[a-f0-9]{64}$'
     or p_limit is null or p_limit < 1 or p_limit > 1000
     or p_window_seconds is null or p_window_seconds < 1 or p_window_seconds > 3600 then
    raise exception 'invalid rate limit parameters';
  end if;
  insert into public.ultron_pairing_rate_limits(key_hash, window_started_at, request_count, updated_at)
  values (p_key_hash, pg_catalog.now(), 1, pg_catalog.now())
  on conflict (key_hash) do update set
    window_started_at = case
      when public.ultron_pairing_rate_limits.window_started_at <=
           pg_catalog.now() - pg_catalog.make_interval(secs => p_window_seconds)
      then pg_catalog.now()
      else public.ultron_pairing_rate_limits.window_started_at end,
    request_count = case
      when public.ultron_pairing_rate_limits.window_started_at <=
           pg_catalog.now() - pg_catalog.make_interval(secs => p_window_seconds)
      then 1
      else public.ultron_pairing_rate_limits.request_count + 1 end,
    updated_at = pg_catalog.now()
  returning request_count into v_count;
  return v_count <= p_limit;
end;
$$;
revoke all on function public.consume_ultron_pairing_rate_limit(text,integer,integer) from public, anon, authenticated;
grant execute on function public.consume_ultron_pairing_rate_limit(text,integer,integer) to service_role;
