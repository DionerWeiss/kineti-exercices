-- Revisão de vídeos de exercícios: catálogo, versões de vídeo no R2 e aprovação.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Catálogo
-- ---------------------------------------------------------------------------

create table public.areas (
  id   text primary key,
  name text not null,
  sort int  not null default 0
);

create table public.exercises (
  slug             text primary key,
  name             text not null,
  description      text not null default '',
  focus            text not null default '',
  area_id          text references public.areas (id),
  props            text not null default '',
  camera_view      text not null default '',
  lib              text not null default '',
  pocketphysio_ids text[] not null default '{}',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index exercises_area_idx on public.exercises (area_id);

-- ---------------------------------------------------------------------------
-- Versões de vídeo (cada upload é uma versão nova; a revisão é por versão)
-- ---------------------------------------------------------------------------

create type public.review_status as enum ('pending', 'approved', 'rejected');

create table public.exercise_videos (
  id                uuid primary key default gen_random_uuid(),
  exercise_slug     text not null references public.exercises (slug) on delete cascade,
  version           int  not null,
  r2_key            text not null unique,
  content_type      text not null,
  size_bytes        bigint not null check (size_bytes > 0),
  original_filename text,
  uploaded_by       uuid references auth.users (id) on delete set null,
  uploaded_by_email text,
  uploaded_at       timestamptz not null default now(),
  status            public.review_status not null default 'pending',
  rejection_reason  text,
  reviewed_by       uuid references auth.users (id) on delete set null,
  reviewed_by_email text,
  reviewed_at       timestamptz,
  unique (exercise_slug, version),
  constraint rejection_needs_reason
    check (status <> 'rejected' or length(btrim(coalesce(rejection_reason, ''))) >= 3)
);

create index exercise_videos_slug_version_idx
  on public.exercise_videos (exercise_slug, version desc);

-- Número da versão e autor são definidos pelo banco, nunca pelo cliente.
create function public.exercise_videos_before_insert()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  perform pg_advisory_xact_lock(hashtext(new.exercise_slug));
  select coalesce(max(v.version), 0) + 1
    into new.version
    from public.exercise_videos v
   where v.exercise_slug = new.exercise_slug;

  if auth.uid() is not null then
    new.uploaded_by := auth.uid();
    new.uploaded_by_email := auth.jwt() ->> 'email';
  end if;

  new.uploaded_at := now();
  new.status := 'pending';
  new.rejection_reason := null;
  new.reviewed_by := null;
  new.reviewed_by_email := null;
  new.reviewed_at := null;
  return new;
end;
$$;

create trigger exercise_videos_before_insert
  before insert on public.exercise_videos
  for each row execute function public.exercise_videos_before_insert();

-- Revisor e data da revisão também vêm do banco.
create function public.exercise_videos_before_update()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.status is distinct from old.status
     or new.rejection_reason is distinct from old.rejection_reason then
    if new.status = 'pending' then
      new.rejection_reason := null;
      new.reviewed_by := null;
      new.reviewed_by_email := null;
      new.reviewed_at := null;
    else
      if new.status = 'approved' then
        new.rejection_reason := null;
      else
        new.rejection_reason := btrim(new.rejection_reason);
      end if;
      new.reviewed_by := auth.uid();
      new.reviewed_by_email := auth.jwt() ->> 'email';
      new.reviewed_at := now();
    end if;
  end if;
  return new;
end;
$$;

create trigger exercise_videos_before_update
  before update on public.exercise_videos
  for each row execute function public.exercise_videos_before_update();

-- ---------------------------------------------------------------------------
-- Lista de revisão: cada exercício com a versão mais recente do vídeo
-- ---------------------------------------------------------------------------

create view public.exercise_review_list
with (security_invoker = true) as
select
  e.slug,
  e.name,
  e.description,
  e.focus,
  e.area_id,
  a.name                              as area_name,
  e.props,
  e.camera_view,
  v.id                                as video_id,
  v.version,
  v.r2_key,
  v.content_type,
  v.status,
  v.rejection_reason,
  v.uploaded_at,
  v.uploaded_by_email,
  v.reviewed_at,
  v.reviewed_by_email,
  coalesce(v.status::text, 'no_video') as review_state,
  coalesce(c.version_count, 0)         as version_count
from public.exercises e
left join public.areas a on a.id = e.area_id
left join lateral (
  select *
    from public.exercise_videos x
   where x.exercise_slug = e.slug
   order by x.version desc
   limit 1
) v on true
left join lateral (
  select count(*)::int as version_count
    from public.exercise_videos y
   where y.exercise_slug = e.slug
) c on true;

-- ---------------------------------------------------------------------------
-- Acesso: só usuários autenticados (cadastro público desligado no Auth)
-- ---------------------------------------------------------------------------

alter table public.areas           enable row level security;
alter table public.exercises       enable row level security;
alter table public.exercise_videos enable row level security;

revoke all on public.areas, public.exercises, public.exercise_videos, public.exercise_review_list
  from anon, authenticated;

grant select on public.areas, public.exercises, public.exercise_videos, public.exercise_review_list
  to authenticated;

-- Upload: o cliente só informa estes campos; o resto vem do trigger.
grant insert (exercise_slug, r2_key, content_type, size_bytes, original_filename)
  on public.exercise_videos to authenticated;

-- Revisão: só status e motivo podem ser alterados.
grant update (status, rejection_reason) on public.exercise_videos to authenticated;

create policy "autenticados leem áreas"
  on public.areas for select to authenticated using (true);

create policy "autenticados leem exercícios"
  on public.exercises for select to authenticated using (true);

create policy "autenticados leem vídeos"
  on public.exercise_videos for select to authenticated using (true);

create policy "autenticados enviam vídeos"
  on public.exercise_videos for insert to authenticated with check (true);

create policy "autenticados revisam vídeos"
  on public.exercise_videos for update to authenticated using (true) with check (true);
