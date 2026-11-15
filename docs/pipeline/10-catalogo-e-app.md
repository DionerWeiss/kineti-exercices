# 10 · Catálogo comparativo e app

## Catálogo local (`E:\mannequin\catalogo`)

```bash
python3 tool/mannequin/compare_catalog.py      # -> E:\mannequin\catalogo\index.html + data.js
```

- Põe lado a lado, por exercício: PocketPhysio, manequim antigo, Lottie e render 3D. Tem sincronia, filtros e notas exportáveis em CSV.
- Os vídeos não são copiados. A página usa caminhos relativos: `../pocketphysio_ref/<pp>.mp4`, `../videos/<job>.mp4`, `../puppet2d/final/<job>.mp4` e `../avatar_man/out/videos_final/<job>.mp4`.
- Textos de `tool/mannequin/catalog.json`. Situação de `final/validation`, `final/pp_review`, `final/visual_review`, `fix/lote_*/report.json`, `pp_removed.json`, `puppet2d/final/manifest.json` e da lista de pendências.
- Rode de novo depois de cada re-render, regeração de Lottie ou revisão.

**Badge de situação:** mostra `fix.status`, o status do **último `report.json` de correção em ordem alfabética** que cita o job, e não o veredito final de `final/review_notes.json`. Por isso ~12 jobs aparecem como "não corrigido" e estão ok ou corrigidos no veredito final. O dono do projeto preferiu não mudar isso (15/11). Para saber o estado real, use `review.csv` / `pendentes_final.json`.

## App Next.js (raiz do repo)

Configuração completa no [README da raiz](../../README.md). Pontos principais:

- **Revisão por upload** (`/exercicios`, `/upload`):
  - exercícios do PP que os vídeos atendem (1.223 exercícios para 688 vídeos), com versões por upload no R2;
  - aprovar ou reprovar (motivo obrigatório);
  - só convidados (Supabase Auth);
  - `npm run seed` importa o catálogo, e `--videos` sobe os MP4 (idempotente).
- **Catálogo** (`/catalogo`):
  - cópia do catálogo comparativo;
  - cada usuário salva a escolha (`manequim`, `lottie`, `render3d`) e a nota na tabela `catalog_reviews` (migração `supabase/migrations/20261115000000_catalog_reviews.sql`, RLS por usuário);
  - API em `app/api/catalogo/avaliacoes/route.ts`.
- **Atualizar o catálogo do app** depois de regenerar o local:
  ```bash
  cp /mnt/e/mannequin/catalogo/data.js public/catalogo/data.js
  node scripts/sync-catalog.mjs                                    # -> app/(app)/catalogo/catalogo.json
  node --env-file=.env.local scripts/upload-catalog.mjs --dry-run  # vídeos para o R2 (CATALOG_VIDEO_ROOT, padrão /mnt/e/mannequin)
  node --env-file=.env.local scripts/upload-catalog.mjs
  ```
  `public/catalogo/index.html` é uma cópia adaptada a `/api/catalogo`. Mudanças no `compare_catalog.html` não chegam lá sozinhas.
- Next.js 16 com mudanças que quebram compatibilidade. Leia `node_modules/next/dist/docs/` antes de mexer no app (veja `AGENTS.md`).

## Textos em português

- `tool/mannequin/texts_pt.json`: `{slug: [nome, descrição, foco, área]}`, escritos à mão. A descrição segue o que o vídeo mostra.
- `python3 tool/mannequin/catalog.py` gera `tool/mannequin/catalog.json`. Os exercícios que já existem na biblioteca Kineti copiam os textos dela.

## Licenças

- desk-break: MIT. Inclua o aviso de `build/desk-break/LICENSE` na tela de licenças do app ao distribuir vídeos ou o modelo.
- Bonecos Dinh: Lottie Simple License.
- Nunca remova marca d'água de vídeo de terceiros. Os vídeos do PP são só referência interna.
