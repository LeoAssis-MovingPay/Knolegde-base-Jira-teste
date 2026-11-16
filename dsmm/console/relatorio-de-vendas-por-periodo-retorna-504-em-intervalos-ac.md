---
title: "Relatório de vendas por período retorna 504 em intervalos acima de 30 dias"
tags: ["dsmm","bug","console","relatorio","vendas","timeout","504","performance"]
created: 2026-11-16
updated: 2026-11-16
tickets: ["DSMM-465"]
sistema: "Console"
tipo: bug
pr: "https://github.com/movingpay/repo-teste/pull/1"
---

# 🐛 Relatório de vendas por período retorna 504 em intervalos acima de 30 dias

> [!summary] Resumo
> O relatório de vendas por período no Console falhava com erro 504 (Gateway Timeout) para intervalos superiores a 30 dias devido a uma query ineficiente que impedia o uso de índice na tabela `vendas_parcelas`. A correção envolveu otimizar a query para usar o índice, adicionar paginação ao endpoint e implementar tratamento de erro no frontend, resultando na geração rápida do relatório.

## Contexto
O módulo 'Vendas - Relatório por período' no [[Console]] (parte do [[BackOffice Subacquirer__fe-modulo-relatorios|Frontend: Relatórios & Vendas]]) permite aos usuários filtrar e visualizar dados de vendas. A funcionalidade é suportada pelo endpoint `GET /api/v3/vendas/relatorio/periodo`, que interage com a tabela `vendas_parcelas` para recuperar os dados.

## Sintoma
O usuário observava lentidão e falha ao tentar filtrar dados de vendas por um período superior a 30 dias no Console.
1. Acessar o Console e navegar até Vendas > Relatório por período.
2. No campo de filtro de período, selecionar um intervalo superior a 30 dias (ex: 01/08/2023 a 31/10/2023).
3. Clicar no botão 'Gerar'.
4. Após aproximadamente 60 segundos, a requisição `GET /api/v3/vendas/relatorio/periodo` falhava com um erro 504 (Gateway Timeout) do ALB. A interface permanecia com um 'spinner' de carregamento infinito, sem mensagem clara de erro.

## Causa raiz
A causa raiz do timeout foi uma query ineficiente na base de dados, especificamente no relatório de vendas. A condição de filtro utilizava `DATE(data_venda) BETWEEN ...`, o que impedia o otimizador de query de usar o índice existente `idx_vendas_data_venda` na tabela `vendas_parcelas`. Isso resultava em um `full scan` na tabela, tornando a consulta muito lenta para grandes volumes de dados (períodos maiores que 30 dias) e excedendo o tempo limite do ALB.

## Solução
A correção foi implementada através do PR fictício de teste: `https://github.com/movingpay/repo-teste/pull/1`.

As seguintes alterações foram realizadas:
*   **Otimização da Query**: O filtro da query foi alterado de `DATE(data_venda) BETWEEN :inicio AND :fim` para `data_venda >= :inicio AND data_venda < :fim + 1 dia`. Esta alteração permitiu que o banco de dados utilizasse eficientemente o índice `idx_vendas_data_venda` na tabela `vendas_parcelas`, evitando o `full scan`.
*   **Paginação**: Foi adicionada paginação ao endpoint, limitando o retorno a 5000 registros por página, o que ajuda a gerenciar a carga de dados.
*   **Tratamento de Erro no Frontend**: O frontend foi atualizado para encerrar o estado de carregamento ('spinner') e exibir uma mensagem de erro clara ao usuário em caso de retorno de um erro 504.

| Cenário | Tempo Antes | Tempo Depois |
| :------ | :---------- | :----------- |
| 90 dias | ~75s        | ~3,2s        |

## Como validar
1. Acessar o Console e navegar até Vendas > Relatório por período.
2. No campo de filtro de período, selecionar um intervalo superior a 30 dias, por exemplo, 90 dias (e.g., 01/08/2023 a 31/10/2023).
3. Clicar no botão 'Gerar'.
4. Verificar que o relatório é gerado e exibido na tela em poucos segundos (validado em produção em ~4s para 90 dias), sem o erro 504 e sem o 'spinner' de carregamento infinito.

## Se acontecer de novo
> [!tip] Como reconhecer e diagnosticar
> *   **Sinais**: Usuários reportando que o "Relatório de vendas por período" não carrega ou exibe erro 504, especialmente para períodos longos. Nos logs do backend, procurar por requisições `GET /api/v3/vendas/relatorio/periodo` que excedem o tempo limite ou erros de query.
> *   **O que verificar primeiro**:
>     1.  A estrutura da query utilizada pelo endpoint `GET /api/v3/vendas/relatorio/periodo` (no código do backend). Verificar se a condição de filtro de data continua otimizada para uso de índices (`data_venda >= :inicio AND data_venda < :fim + 1 dia`).
>     2.  A existência e integridade do índice `idx_vendas_data_venda` na tabela `vendas_parcelas`.
>     3.  Logs do ALB e da aplicação para identificar se o timeout ainda está ocorrendo e qual o tempo de resposta da query no banco de dados.
> *   **Prevenção ou débitos técnicos**: Monitorar os tempos de execução de queries críticas em relatórios para identificar degradação de performance antes que atinja os limites de timeout. Considerar a implementação de dashboards de performance de queries.

## Referências
*   PR: https://github.com/movingpay/repo-teste/pull/1
*   Notas relacionadas: [[BackOffice Subacquirer__fe-modulo-relatorios]]

## Ocorrências

### DSMM-465 · 2026-11-16 · Leonardo Ribeiro De Assis
Primeira ocorrência: deu origem a esta nota. [Ticket](https://SEU-SITE.atlassian.net/browse/DSMM-465) · [PR](https://github.com/movingpay/repo-teste/pull/1)
