-- Avaliações pessoais do catálogo de comparação.
create table public.catalog_reviews (
  user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  exercise_id text not null check (length(exercise_id) between 1 and 200),
  note text not null default '' check (length(note) <= 10000),
  choice text check (choice in ('manequim', 'lottie', 'render3d')),
  updated_at timestamptz not null default now(),
  primary key (user_id, exercise_id)
);
alter table public.catalog_reviews enable row level security;
grant select, insert, update on public.catalog_reviews to authenticated;
create policy "usuários leem próprias avaliações" on public.catalog_reviews for select to authenticated using (user_id = auth.uid());
create policy "usuários criam próprias avaliações" on public.catalog_reviews for insert to authenticated with check (user_id = auth.uid());
create policy "usuários alteram próprias avaliações" on public.catalog_reviews for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
