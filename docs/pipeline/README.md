# Pipeline de exercícios animados Kineti

Documentação de como os vídeos de exercícios são criados, revisados, comparados com o PocketPhysio, corrigidos e estendidos para exercícios novos. Vale para os três formatos entregues: **render 3D** (avatar low-poly), **Lottie 2D** e os vídeos antigos do **manequim**.

Estado em 15/11/2026: 688 vídeos (jobs), 1.314 exercícios do PocketPhysio atendidos. No 3D, 248 ok, 407 corrigidos e 33 pendentes. No Lottie, 576 ok e 103 com limitação. O resumo da entrega está em `E:\mannequin\avatar_man\final\RESUMO_FINAL.md`.

## Por onde começar

| Quero… | Leia |
|---|---|
| Entender as peças e como os dados fluem | [01 · Arquitetura](01-arquitetura.md) |
| Preparar a máquina e saber onde fica cada arquivo | [02 · Ambiente e arquivos](02-ambiente.md) |
| Escrever ou ajustar um movimento | [03 · Criação de movimentos](03-movimentos.md) |
| Escolher câmera e acessórios | [04 · Câmera e acessórios](04-camera-e-props.md) |
| Renderizar um lote | [05 · Render](05-render.md) |
| Revisar vídeos (QA automático e visual) | [06 · Revisão em 4 camadas](06-revisao.md) |
| Comparar com o PocketPhysio | [07 · Comparação com o PocketPhysio](07-pocketphysio.md) |
| Corrigir lotes e processar notas do cliente | [08 · Rodadas de correção](08-correcao.md) |
| Gerar os Lotties 2D | [09 · Lottie 2D](09-lottie.md) |
| Atualizar o catálogo comparativo e o app | [10 · Catálogo e app](10-catalogo-e-app.md) |
| Adicionar exercícios novos | [11 · Novos exercícios](11-novos-exercicios.md) |
| Saber o que não funciona e o que já foi decidido | [12 · Limites, decisões e lições](12-limites-e-decisoes.md) |
| Reaproveitar as instruções dos agentes de revisão | [agentes/](agentes/) |

## Regras que valem para tudo

1. **O vídeo do PocketPhysio é a referência.** Posição inicial, amplitude, braços, contatos e ritmo seguem o vídeo, não o texto nem a versão anterior.
2. **Corrija na fonte.** Mude o movimento (`kineti_moves.json`, `deskbreak_moves.json`), o construtor (`kineti_builder.py`) ou o passo de mãos (`plant_hands.py`). Nunca edite o vídeo. Se não der, marque `pendente` com o motivo.
3. **Ao corrigir um exercício, corrija os irmãos.** Os exercícios da mesma família, com os mesmos acessórios ou com o mesmo tipo de movimento, recebem a mesma correção quando fizer sentido.
4. **Meça antes de olhar.** Uma imagem pequena engana: uma mão que parece apoiada pode estar 5 cm acima do chão. Confira as posições das juntas e o `_low` de mãos e pés, depois veja os quadros em tamanho real.
5. **Não use suavização global** para esconder trancos: ela solta os contatos.
6. **Não mude a aparência do avatar** (corpo, malha, roupa, cabelo) sem perguntar ao dono do projeto. O visual aprovado é o de `videos_v9`.
7. **Não use Gemini nem Vertex.** Textos, classificações e revisões são feitos à mão ou por agentes que olham as imagens. Pergunte antes de usar qualquer outro modelo externo pago.
8. **Não sobrescreva** `E:\mannequin\videos` (vídeos antigos do manequim) nem a lib de render `exercises_final.blend` durante um render. Para testar, use uma cópia (`exercises_scratch.blend` ou a lib de um diretório `fix/`).
9. **Não rode `sheet` nem `render` sem lista de ids.** Sem ids, o comando processa os 688 jobs.
10. **Faça backup da lib antes de sincronizar muitos movimentos:** `exercises_final_before_<motivo>.blend`.

## Glossário

| Termo | Significado |
|---|---|
| **job** | Um vídeo. Chave de `tool/mannequin/jobs.json`, com `lib`, `view`, `props`, `pocketphysio` e, opcionalmente, `move` e `frame`. |
| **move / movimento** | A animação em poses-chave (JSON). Um job toca o move de mesmo id ou o do campo `move`. Vários jobs podem compartilhar um move. |
| **action** | O move já construído, dentro de um `.blend` (mesmo nome do move). |
| **lib** | O `.blend` com o rig, o corpo (manequim ou avatar) e as actions. A lib final é `E:\mannequin\avatar_man\exercises_final.blend`. |
| **desk-break** | Projeto MIT de onde vêm o rig, o manequim, o construtor e 435 movimentos ([github.com/shlomorsh/desk-break](https://github.com/shlomorsh/desk-break), commit `8d475aa`). |
| **builder** | `kineti_builder.py`: transforma poses-chave em curvas, aterra o corpo e prende os contatos. |
| **plant_hands** | Passo de render que reapoia o avatar no chão e espalma as mãos. |
| **PP** | PocketPhysio, o catálogo de referência (1.581 exercícios publicados). |
| **lote** | Grupo de ~50 jobs revisados juntos (`final/lotes/lote_NN.txt`). `R01`–`R15` são lotes de re-render; `R2a`, `C1` etc. são rodadas de correção. |
| **camadas 1–4** | QA de pose, QA de movimento/vídeo, comparação com o PP e revisão visual ([06](06-revisao.md)). |
| **ok / corrigido / pendente** | Veredito final por job. `corrigido` = havia defeito e a correção aparece no vídeo novo. |
| **igual / próximo / diferente** | Veredito por id do PP ([07](07-pocketphysio.md)). `diferente` tira o id do job. |
| **irmãos** | Jobs com o mesmo problema (mesma família de movimento, mesmos props) que recebem a mesma correção. |
