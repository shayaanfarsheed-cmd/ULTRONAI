begin;

create extension if not exists pgtap with schema extensions;
select plan(19);

select ok(
  not has_table_privilege('anon', 'public.ultron_devices', 'SELECT')
  and not has_table_privilege('authenticated', 'public.ultron_devices', 'SELECT'),
  'device registry is not directly readable by browser roles'
);
select ok(
  not has_table_privilege('anon', 'public.ultron_pairing_challenges', 'SELECT')
  and not has_table_privilege('authenticated', 'public.ultron_pairing_challenges', 'SELECT'),
  'pairing challenges are not directly readable by browser roles'
);
select ok(
  not has_table_privilege('anon', 'public.ultron_pairing_rate_limits', 'SELECT')
  and not has_table_privilege('authenticated', 'public.ultron_pairing_rate_limits', 'SELECT'),
  'rate-limit records are not directly readable by browser roles'
);
select ok(
  not has_function_privilege('anon', 'public.consume_ultron_pairing_challenge(uuid,text,text,text,jsonb,text)', 'EXECUTE')
  and not has_function_privilege('authenticated', 'public.consume_ultron_pairing_challenge(uuid,text,text,text,jsonb,text)', 'EXECUTE'),
  'challenge consume RPC is not executable by browser roles'
);
select ok(
  not has_function_privilege('anon', 'public.consume_ultron_pairing_rate_limit(text,integer,integer)', 'EXECUTE')
  and not has_function_privilege('authenticated', 'public.consume_ultron_pairing_rate_limit(text,integer,integer)', 'EXECUTE'),
  'rate-limit RPC is not executable by browser roles'
);

select ok(
  (select relrowsecurity from pg_class where oid = 'public.ultron_devices'::regclass),
  'device registry has row-level security enabled'
);
select ok(
  (select relrowsecurity from pg_class where oid = 'public.ultron_pairing_challenges'::regclass),
  'pairing challenges have row-level security enabled'
);
select ok(
  (select relrowsecurity from pg_class where oid = 'public.ultron_pairing_rate_limits'::regclass),
  'rate-limit records have row-level security enabled'
);
select ok(
  not (select prosecdef from pg_proc where oid = 'public.consume_ultron_pairing_challenge(uuid,text,text,text,jsonb,text)'::regprocedure),
  'challenge consume RPC runs as security invoker'
);
select ok(
  not (select prosecdef from pg_proc where oid = 'public.consume_ultron_pairing_rate_limit(text,integer,integer)'::regprocedure),
  'rate-limit RPC runs as security invoker'
);

insert into auth.users (id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('a1000000-0000-4000-8000-000000000001', 'authenticated', 'authenticated', 'pairing-owner-a@test.invalid', '', now(), now(), now()),
  ('a1000000-0000-4000-8000-000000000002', 'authenticated', 'authenticated', 'pairing-owner-b@test.invalid', '', now(), now(), now())
on conflict (id) do nothing;

set local role service_role;
select set_config('request.jwt.claim.role', 'service_role', true);

insert into public.ultron_pairing_challenges (id, owner_id, code_hash, expires_at)
values (
  'a2000000-0000-4000-8000-000000000001',
  'a1000000-0000-4000-8000-000000000001',
  repeat('a', 64),
  now() + interval '5 minutes'
);

do $$
declare i integer;
begin
  for i in 1..5 loop
    perform public.consume_ultron_pairing_challenge(
      'a2000000-0000-4000-8000-000000000001',
      repeat('b', 64), 'bad-attempt', 'linux', '{}'::jsonb, repeat('c', 64)
    );
  end loop;
end $$;

select is(
  (select attempts from public.ultron_pairing_challenges where id = 'a2000000-0000-4000-8000-000000000001'),
  5::smallint,
  'five failed attempts are counted'
);
select is(
  public.consume_ultron_pairing_challenge(
    'a2000000-0000-4000-8000-000000000001',
    repeat('a', 64), 'locked-out', 'linux', '{}'::jsonb, repeat('d', 64)
  ),
  null::uuid,
  'a correct code is rejected after five failed attempts'
);

insert into public.ultron_pairing_challenges (id, owner_id, code_hash, created_at, expires_at)
values (
  'a2000000-0000-4000-8000-000000000002',
  'a1000000-0000-4000-8000-000000000002',
  repeat('e', 64),
  now() - interval '10 minutes',
  now() - interval '5 minutes'
);
select is(
  public.consume_ultron_pairing_challenge(
    'a2000000-0000-4000-8000-000000000002',
    repeat('e', 64), 'expired-device', 'linux', '{}'::jsonb, repeat('f', 64)
  ),
  null::uuid,
  'expired challenges cannot be redeemed'
);

insert into public.ultron_pairing_challenges (id, owner_id, code_hash, expires_at)
values (
  'a2000000-0000-4000-8000-000000000003',
  'a1000000-0000-4000-8000-000000000001',
  repeat('1', 64),
  now() + interval '5 minutes'
);
select isnt(
  public.consume_ultron_pairing_challenge(
    'a2000000-0000-4000-8000-000000000003',
    repeat('1', 64), 'valid-device', 'linux', '{}'::jsonb, repeat('2', 64)
  ),
  null::uuid,
  'a valid challenge creates a device'
);
select is(
  public.consume_ultron_pairing_challenge(
    'a2000000-0000-4000-8000-000000000003',
    repeat('1', 64), 'duplicate-device', 'linux', '{}'::jsonb, repeat('3', 64)
  ),
  null::uuid,
  'a consumed challenge cannot be redeemed again'
);
select is(
  (select count(*)::integer from public.ultron_devices where owner_id = 'a1000000-0000-4000-8000-000000000001'),
  1,
  'successful redemption creates exactly one device for the challenge owner'
);

select ok(
  public.consume_ultron_pairing_rate_limit(repeat('9', 64), 10, 60),
  'first request is within the rate limit'
);
select is(
  (select count(*)::integer
   from generate_series(1, 9) as n
   where public.consume_ultron_pairing_rate_limit(repeat('9', 64), 10, 60)),
  9,
  'requests two through ten remain within the rate limit'
);
select ok(
  not public.consume_ultron_pairing_rate_limit(repeat('9', 64), 10, 60),
  'eleventh request is rejected'
);

select * from finish();
rollback;
