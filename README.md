# Kineti · revisão de vídeos de exercícios

App Next.js para enviar vídeos de exercícios ao Cloudflare R2 e aprovar ou reprovar cada versão. Login e banco ficam no Supabase.

O pipeline que gera os vídeos (manequim, Blender) continua em [`tool/`](tool/README.md) e [`tool/mannequin/`](tool/mannequin/README.md).

## Telas

- **/login**: e-mail e senha, só para convidados. Inclui recuperação de senha.
- **/exercicios**: lista com a versão mais recente de cada vídeo, descrição, foco e área. Tem filtros por status (pendentes, reprovados, aprovados, sem vídeo), área e busca. Os botões são **Aprovar**, **Reprovar** (o motivo é obrigatório) e **Desfazer revisão**.
- **/exercicios/[slug]**: histórico de todas as versões, com quem enviou, quem revisou e o motivo de cada reprovação.
- **/upload**: escolha o exercício e o arquivo (MP4, WebM ou MOV, até 1 GB). O navegador envia direto ao R2 por URL assinada, e cada envio vira uma versão nova, pendente.

## Como funciona

- **Exercícios** são os do PocketPhysio que o manequim atende (exercícios com o mesmo nome e o mesmo vídeo viram um só, guardando todos os ids), mais os vídeos só do Kineti. Hoje são 1.223 exercícios para 688 vídeos.
- Um vídeo do manequim fica uma vez no R2 (`mannequin/<video>.mp4`) e é a versão 1 de todos os exercícios que o usam. **A revisão é por exercício**: o mesmo vídeo pode servir para um exercício e não para outro. Um upload novo vale só para o exercício escolhido.
- Cada upload cria uma linha em `exercise_videos`. O banco define `version`, quem enviou, quem revisou e as datas; o cliente só pode alterar `status` e `rejection_reason` (permissão por coluna).
- Uma check constraint impede `rejected` sem motivo (mínimo de 3 caracteres).
- A view `exercise_review_list` junta cada exercício à sua versão mais recente.
- O R2 é privado. Para assistir, o app gera URLs assinadas de 1 hora, a menos que `R2_PUBLIC_URL` esteja definida.

## Configuração

### 1. Supabase

1. Crie um projeto e rode, em ordem, os arquivos de [`supabase/migrations/`](supabase/migrations/) no SQL Editor (ou use `supabase db push`).
2. Em **Authentication → Sign In / Providers**, desligue **Allow new users to sign up**.
3. Em **Authentication → URL Configuration**, defina o **Site URL** (ex.: `http://localhost:3000`) e adicione `http://localhost:3000/auth/confirm` às Redirect URLs.
4. Em **Authentication → Email Templates**, troque o link dos templates abaixo para que o login aconteça no servidor:
   - **Invite user**: `{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=invite&next=/definir-senha`
   - **Reset password**: `{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=recovery&next=/definir-senha`
5. Convide pessoas em **Authentication → Users → Invite user**. Quem recebe o convite clica no link e cria a senha. Você também pode criar o usuário já com senha em **Add user → Create new user**.

### 2. Cloudflare R2

1. Crie um bucket (ex.: `kineti-exercise-videos`).
2. Em **R2 → Manage API tokens**, crie um token com **Object Read & Write** restrito ao bucket.
3. Em **Settings → CORS policy** do bucket, cole [`r2-cors.json`](r2-cors.json) e acrescente o domínio de produção em `AllowedOrigins`. Sem isso, o upload falha no navegador.

### 3. App

```bash
cp .env.example .env.local   # preencha Supabase e R2
npm install
npm run seed                 # importa áreas e exercícios (tool/mannequin/catalog.json + research/pocketphysio)
npm run seed -- --videos     # opcional: sobe os MP4 de build/mannequin/videos e liga cada exercício ao seu
npm run dev
```

O seed é idempotente: atualiza os exercícios existentes, só envia arquivos que ainda não estão no R2 e só liga vídeo a exercícios sem nenhuma versão. `--prune` apaga exercícios que saíram do catálogo, mas preserva os que já foram revisados ou receberam upload. Use `--dry-run` para ver o que ele faria.

## Scripts

| Comando | O que faz |
| --- | --- |
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Build de produção |
| `npm run lint` / `npm run typecheck` | ESLint e TypeScript |
| `npm run seed` | Importa o catálogo para o Supabase (`--videos`, `--prune`, `--dry-run`) |

## Notas

- Next.js 16 com Cache Components: tudo que lê a sessão fica dentro de `<Suspense>`, e o `proxy.ts` (antigo middleware) renova a sessão e manda quem não está logado para `/login`.
- `SUPABASE_SERVICE_ROLE_KEY` só é usada pelo `scripts/seed.mjs`. O app usa a chave publishable e respeita o RLS.
- Ao distribuir os vídeos do manequim, mantenha o aviso de copyright MIT do desk-break.
