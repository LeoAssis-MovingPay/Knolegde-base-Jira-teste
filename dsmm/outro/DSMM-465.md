---
ticket: DSMM-465
titulo: "CONSOLE - Relatório de vendas por período retorna 504 em intervalos acima de 30 dias"
sistema: Outro
tipo: bug
tags: ["504", "timeout", "relatório de vendas", "performance", "índice", "paginação", "Console"]
responsavel: Leonardo Ribeiro De Assis
resolvido_em: 2026-11-16
jira: https://movingpay.atlassian.net/browse/DSMM-465
pr: 
---

# DSMM-465 — CONSOLE - Relatório de vendas por período retorna 504 em intervalos acima de 30 dias

Sistema: [[Outro]]

## Sintoma
Usuários enfrentam lentidão e falha (erro `504 Gateway Timeout`) ao tentar filtrar dados no módulo 'Vendas - Relatório por período' do Console por um período superior a 30 dias. A requisição `GET /api/v3/vendas/relatorio/periodo` excede o tempo limite de 60 segundos, e a interface exibe um 'spinner' de carregamento infinito.

## Causa raiz
A query do relatório `GET /api/v3/vendas/relatorio/periodo` fazia um `full scan` na tabela `vendas_parcelas` porque o filtro utilizava `DATE(data_venda) BETWEEN ...`, o que impedia o uso do índice `idx_vendas_data_venda`. Isso resultava em consultas que excediam o tempo limite do Application Load Balancer (ALB).

## Solução
1. A query foi otimizada trocando o filtro para `data_venda >= :inicio AND data_venda < :fim + 1 dia`, permitindo o uso do índice `idx_vendas_data_venda`. 2. Adição de paginação ao `endpoint` (`limit 5000 por página`). 3. No frontend, foi implementado o encerramento do `loading` em caso de erro e a exibição de uma mensagem clara para o erro `504`.

## Como validar
Acessar o Console, navegar até 'Vendas > Relatório por período'. Selecionar um intervalo de período superior a 30 dias (ex: 90 dias) e clicar em 'Gerar'. O relatório deve ser gerado corretamente em aproximadamente 4 segundos, sem retornar erro `504`.

## Observações
A correção resultou em uma melhoria de performance significativa para a geração de relatórios de vendas com períodos longos, passando de aproximadamente 75 segundos para 3,2 segundos em homologação para 90 dias de dados, e 4 segundos em produção.
