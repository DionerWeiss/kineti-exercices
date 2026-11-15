# 07 · Comparação com o PocketPhysio

O PocketPhysio (PP) é a referência clínica. O cliente compara cada exercício com o vídeo do PP e repara em ritmo, lado da câmera e detalhes de apoio, não só em erros grosseiros.

## Fonte

- `research/pocketphysio/exercicios.json` (fora do git): 1.756 exercícios, 1.581 publicados. Campos usados: `id` (24 caracteres), `nome_pt`, `descricao_pt`, `observacoes`, `posicao`.
- Coletado em 07/11 pela API interna `/api/physiolight/exercises?limit=5000&live=false&lang=en`, chamada de dentro da sessão logada no navegador. Os vídeos ficam num bucket S3 público.
- 147 itens têm o vídeo genérico "Demo Video" e só podem ser julgados pelo texto. Alguns arquivos do S3 respondem 403.
- `tool/pocketphysio/score.py` recalcula a rubrica de esforço sem LLM. Os passes Gemini (`analyze.py`, `match_library.py`) foram removidos do repo em 15/11 (estão no histórico, commit `45091ee`) e não devem ser rodados de novo.
- Cada job lista em `jobs.json[job].pocketphysio` os ids que atende: 688 vídeos para 1.314 ids.

## Ferramentas

```bash
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py fetch <jobs>     # cache em E:\mannequin\pocketphysio_ref\<id>.mp4
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py compare <jobs>   # out/compare/<job>.mp4 e .png
tool/mannequin/ops/pp.sh <ppid…>                                                          # texto do PP + mosaico de 8 quadros
```

- `status.json` no cache: `ok`, `403`, `erro` ou `placeholder` (arquivo compartilhado por exercícios diferentes). Esses ids são comparados pelo texto (`ref: texto`).
- `compare` acha o ciclo de cada lado (autocorrelação no PP, excursões do rig no nosso) e toca o PP na velocidade que casa com o nosso ciclo. Ele gera:
  - `<job>.mp4`: PP à esquerda, nosso à direita;
  - `<job>.png`: para cada id, uma linha com início, pico e retorno, e a nossa linha embaixo (8 linhas por folha).
- Os vídeos do PP têm de 8 a 107 MB cada (~25 GB no total).

## Duas revisões contra o PP

### A · Validação por job (o estilo do cliente)

Instruções: [agentes/validation_brief.md](agentes/validation_brief.md). Escolha o id do PP que melhor representa o job e compare:

1. **posição inicial:** deitado, sentado ou em pé; pernas esticadas ou dobradas; onde cada membro começa; pés planos;
2. **amplitude:** joelho até o chão, profundidade do agachamento, altura do braço;
3. **braços e mãos;**
4. **contatos:** pé plano ou só o calcanhar; joelho, mão ou pé que deveria ficar parado e desliza; pé no ar;
5. **ritmo:** muito lento ou muito rápido; pausas longas que o vídeo não tem;
6. **movimento errado.**

Veredito por job: `ok`, `ajustar` (mesmo exercício, correções pontuais) ou `refazer` (movimento errado). As notas são curtas e em português, como as do cliente:

> "mini-squat: precisa se abaixar um pouco mais, precisa ficar igual do vídeo"
> "knee-push-up: os joelhos devem permanecer fixos no lugar"
> "side-plank: pé encostado no chão, corpo em linha diagonal, igual ao PocketPhysio"

Saída: `final/validation/lote_NN.json`. Essa saída alimenta a rodada de correção ([08](08-correcao.md)).

### B · Camada 3: veredito por id do PP

Instruções: [agentes/layer3_brief.md](agentes/layer3_brief.md). Para cada id do PP de cada job:

| `pp_match` | Quando |
|---|---|
| `igual` | Mesma posição do corpo, mesma(s) articulação(ões) no mesmo sentido, amplitude parecida. Pequenas diferenças são aceitas: lugar da mão, tipo de cadeira, velocidade, um lado em vez de alternado, pés descalços |
| `próximo` | Mesmo padrão com uma variante clara: apoio ou posição (beira da cama × cadeira), amplitude bem diferente, braços fazendo algo que importa, um acessório faltando |
| `diferente` | Outro movimento (outra articulação, outro plano, outro exercício): quem seguisse o nosso vídeo faria outro exercício. Use com parcimônia |

Saída: `final/pp_review/lote_NN.json`. `ops/merge_pp.py NN` junta em `review_pp.json`. Os ids `diferente` **saem do job** e vão para `tool/mannequin/pp_removed.json` com o status "precisa de vídeo próprio" (34 até agora).

Resultado final: 708 igual, 489 próximo, 35 diferente, 82 não comparados.

## O que o cliente cobrou (lote 01, 15/11)

- "Não está igual ao PocketPhysio": o vídeo do PP vale mais que o texto e que a versão anterior.
- Movimentos frontais vistos de frente.
- Movimentos de mesa mais lentos.
- Ombros largos demais sentado na cama; andador alto demais; pés parados no sentar e levantar; perna mais alta no apoio unipodal; pés alinhados no tandem.
- Pedido explícito: "avalie e aplique a todos os exercícios que fizerem sentido". Toda correção vale para os irmãos.

## Um modelo de vídeo poderia fazer essa revisão?

Avaliado em 15/11, sem testar. Um modelo bom de vídeo deve pegar as diferenças grosseiras: lado ou vista, amplitude, movimento diferente, props faltando, ritmo muito diferente. Ele deve falhar nos detalhes que mais deram trabalho: mão 2–3 cm no ar, mão em garra, pé deslizando 2 cm, tranco de 1–2 quadros, emenda do loop. Para esses, as métricas das camadas 1 e 2 são mais confiáveis.

Teste proposto, caso o uso seja liberado (hoje Gemini e Vertex estão vetados): rodar o modelo nos vídeos de antes da correção do lote 01 e medir quantas das 32 notas do cliente ele encontra e quantos falsos positivos gera. As notas estão em `E:\mannequin\avatar_man\ops\user_notes_l01.csv`.
