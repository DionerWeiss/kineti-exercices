# Instruções dos agentes de revisão e correção

Instruções (em inglês) usadas nas rodadas de 13–15/11. Cada uma serve de prompt para um agente que trabalha num lote. Troque `NN` pelo número do lote antes de usar.

| Arquivo | Etapa | Escreve |
|---|---|---|
| [validation_brief.md](validation_brief.md) | Validação por job contra o PP, no estilo do cliente (ok / ajustar / refazer) | `final/validation/lote_NN.json` |
| [layer3_brief.md](layer3_brief.md) | Camada 3: veredito por id do PP (igual / próximo / diferente) | `final/pp_review/lote_NN.json` |
| [layer4_brief.md](layer4_brief.md) | Camada 4: revisão visual da primeira passada | `final/visual_review/lote_NN.json` |
| [layer4R_brief.md](layer4R_brief.md) | Camada 4 de um lote re-renderizado (olha todos os jobs) | `final/visual_review/lote_RNN.json` |
| [fix_brief.md](fix_brief.md) | Correção de movimentos num diretório isolado | `fix/lote_NN/report.json` + `moves/` |
| [client_round_brief.md](client_round_brief.md) | Rodada de notas do cliente, aplicando também aos irmãos (complementa o fix_brief) | `fix/lote_CN/report.json` |
| [lottie_all_brief.md](lottie_all_brief.md) | Geração e revisão dos Lotties de todos os jobs | `puppet2d/final/` |
| [puppet_brief.md](puppet_brief.md) | Mãos, mãos espalmadas e props do boneco lateral (histórico) | `tool/puppet2d/drive_puppet.py` |
| [front_brief.md](front_brief.md) | Criação do boneco frontal e do `pick_view` (histórico) | `tool/puppet2d/drive_front.py` |

Caminhos que antes apontavam para a pasta temporária da sessão foram trocados por `/mnt/e/mannequin/avatar_man/ops/` (estado das rodadas: `notes_plan.json`, `pendentes_final.txt`, `user_notes_l01.csv`, mosaicos) e por `tool/mannequin/ops/` (scripts).

Regras comuns a todas as instruções: não editar o repo nem a lib de render fora do papel do agente; só stills enquanto houver render no GPU; nada de suavização global; não mudar o visual do avatar; sem Gemini/Vertex; notas curtas em português.
