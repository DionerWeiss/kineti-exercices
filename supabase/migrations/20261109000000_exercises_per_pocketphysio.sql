-- Um exercício por exercício do PocketPhysio (mesmo nome + mesmo vídeo = um só).
-- O mesmo arquivo de vídeo do manequim passa a servir vários exercícios,
-- mas a revisão continua por exercício.

-- O mesmo objeto do R2 pode ser a versão de vários exercícios (só não duas vezes no mesmo).
alter table public.exercise_videos drop constraint exercise_videos_r2_key_key;
alter table public.exercise_videos
  add constraint exercise_videos_exercise_key_unique unique (exercise_slug, r2_key);
create index exercise_videos_r2_key_idx on public.exercise_videos (r2_key);

-- Origem do exercício e vídeo do manequim que o atende.
alter table public.exercises
  add column source     text not null default 'kineti',
  add column video_slug text,
  add column video_name text;
create index exercises_video_slug_idx on public.exercises (video_slug);

-- Colunas novas entram no fim (exigência do create or replace view).
create or replace view public.exercise_review_list
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
  coalesce(c.version_count, 0)         as version_count,
  e.source,
  e.video_slug,
  e.video_name,
  coalesce(s.shared_count, 1)          as shared_count,
  e.pocketphysio_ids
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
) c on true
left join lateral (
  select count(*)::int as shared_count
    from public.exercises z
   where z.video_slug = e.video_slug
) s on e.video_slug is not null;

grant select on public.exercise_review_list to authenticated;
