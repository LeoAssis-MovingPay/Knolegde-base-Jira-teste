# Base de conhecimento DSMM — MovingPay

Notas de resolução dos chamados **DSMM** (bugs e melhorias de software).
Cada nota é gerada automaticamente pelo n8n quando o ticket é resolvido no Jira,
revisada pelo responsável no Slack e publicada aqui.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `dsmm/<sistema>/` | Uma nota por ticket (`DSMM-123.md`) |
| `templates/` | Modelo da nota |
| `n8n/` | Export do workflow e prompts da IA |
| `scripts/` | Geração do índice |
| `docs/` | Como funciona o fluxo e como contribuir |
| `.github/workflows/` | Action que atualiza o índice abaixo |

## Índice

> Gerado automaticamente por `scripts/gerar_indice.py` — não edite entre os marcadores.

<!-- INDICE:INICIO -->
**Total:** 7 notas

### BackOffice (2)

| Nota | Tickets | Tipo | Atualizada em |
|---|---|---|---|
| [Adição do campo 'observação' em relatório de transferências no Console Contas a Pagar](dsmm/backoffice/adicao-do-campo-observacao-em-relatorio-de-transferencias-no.md) | DSMM-30 | bug | 2026-11-17 |
| [Transações não exibidas na tela de visualização sem filtro de Estabelecimento Comercial (EC)](dsmm/backoffice/transacoes-nao-exibidas-na-tela-de-visualizacao-sem-filtro.md) | DSMM-66 | bug | 2026-11-17 |

### Console (1)

| Nota | Tickets | Tipo | Atualizada em |
|---|---|---|---|
| [Relatório de vendas por período retorna 504 em intervalos acima de 30 dias](dsmm/console/relatorio-de-vendas-por-periodo-retorna-504-em-intervalos-ac.md) | DSMM-465 | bug | 2026-11-16 |

### Manager (1)

| Nota | Tickets | Tipo | Atualizada em |
|---|---|---|---|
| [Transações pagas não aparecem na conciliação de recebíveis sem filtro de EC](dsmm/manager/transacoes-pagas-nao-aparecem-na-conciliacao-de-recebiveis.md) | DSMM-71 | bug | 2026-11-17 |

### Outro (3)

| Nota | Tickets | Tipo | Atualizada em |
|---|---|---|---|
| [Carregamento infinito na aba de Recebimentos do Portal do Distribuidor](dsmm/outro/carregamento-infinito-na-aba-de-recebimentos-do-portal-do-di.md) | DSMM-34 | bug | 2026-11-17 |
| [Venda não splitada devido a validação incorreta de acordo comercial no Split Pós-Venda](dsmm/outro/venda-nao-splitada-devido-a-validacao-incorreta-de-acordo-co.md) | DSMM-85 | bug | 2026-11-17 |
| [[TESTE KB] CONSOLE - Relatório de vendas por período retorna 504 em intervalos acima de 30 dias](dsmm/outro/DSMM-465.md) | DSMM-465 | bug | 2026-11-16 |
<!-- INDICE:FIM -->
