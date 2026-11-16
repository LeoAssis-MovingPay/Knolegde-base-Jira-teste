---
ticket: DSMM-465
titulo: "[TESTE KB] CONSOLE - Relatório de vendas por período retorna 504 em intervalos acima de 30 dias"
sistema: Outro
tipo: bug
tags: ["Console", "Relatório de vendas", "Performance", "Timeout", "504", "API"]
responsavel: Leonardo Ribeiro De Assis
resolvido_em: 2026-11-16
jira: https://movingpay.atlassian.net/browse/DSMM-465
pr: 
---

# DSMM-465 — [TESTE KB] CONSOLE - Relatório de vendas por período retorna 504 em intervalos acima de 30 dias

Sistema: [[Outro]]

## Sintoma
Ao selecionar e aplicar um filtro de período maior que 30 dias na tela de 'Vendas - Relatório por período', a requisição `GET /api/v3/vendas/relatorio/periodo` excede o tempo limite de 60 segundos. Consequentemente, o Application Load Balancer (ALB) retorna um erro `504` (Gateway Timeout) e a interface do usuário exibe um 'spinner' de carregamento infinito, sem nenhuma mensagem de erro clara para o usuário.

## Causa raiz
A query do relatório fazia full scan na tabela `vendas_parcelas` porque o filtro usava `DATE(data_venda) BETWEEN ...`, o que impedia o uso do índice `idx_vendas_data_venda`.

## Solução
1. Troca do filtro da query para `data_venda >= :inicio AND data_venda < :fim + 1 dia` para permitir o uso do índice `idx_vendas_data_venda`.
2. Adição de paginação no endpoint (`limit 5000` por página).
3. No frontend, tratamento para encerrar o loading em caso de erro e exibir mensagem específica para o erro `504`.

## Como validar
1. Acessar o Console e navegar até `Vendas > Relatório por período`.
2. No campo de filtro de período, selecionar um intervalo superior a 30 dias (ex: 01/08/2023 a 31/10/2023).
3. Clicar no botão 'Gerar'.
4. Observar que o relatório é gerado em tempo hábil (ex: 90 dias de dados em ~4s) e sem o retorno do erro `504`.

## Observações
Este ticket foi utilizado como teste para a base de conhecimento (KB).
Nota de resolução publicada em: `https://github.com/movingpay/base-conhecimento-dsmm/blob/main/dsmm/outro/DSMM-465.md`.
