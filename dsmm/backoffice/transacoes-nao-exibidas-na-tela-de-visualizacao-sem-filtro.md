---
title: "Transações não exibidas na tela de visualização sem filtro de Estabelecimento Comercial (EC)"
tags: ["dsmm","bug","backoffice","transacoes","filtro","exibicao","ec"]
created: 2026-11-17
updated: 2026-11-17
tickets: ["DSMM-66"]
sistema: "BackOffice"
tipo: bug
pr: ""
---

# 🐛 Transações não exibidas na tela de visualização sem filtro de Estabelecimento Comercial (EC)

> [!summary] Resumo
> Usuários não conseguiam visualizar transações na tela do BackOffice sem aplicar um filtro de Estabelecimento Comercial (EC), resultando na mensagem 'Não há recebíveis no período solicitado...'. A causa inferida foi um comportamento inesperado na consulta do backend que exigia o filtro de EC. A solução ajustou a lógica da consulta para exibir as transações por padrão, mesmo sem o filtro aplicado.

## Contexto
O problema ocorreu na tela de visualização de transações do [[BackOffice Subacquirer__bo-modulo-transacoes]], que faz parte do módulo de gestão de transações do BackOffice. Esta funcionalidade permite aos vendedores e administradores visualizar o extrato de transações pagas para conciliação financeira, consumindo o endpoint `/api/v3/transacoes`.

## Sintoma
Ao acessar a tela de visualização de transações, o sistema exibia a mensagem 'Não há recebíveis no período solicitado, verifique os filtros e tente novamente.', e todos os valores agregados (Valor Bruto, Taxa Administrativa, Custo Antecipação, Valor Líquido) apareciam zerados. A lista de transações permanecia vazia.

Como reproduzir:
1. Acessar a tela de visualização de transações no BackOffice.
2. Não aplicar nenhum filtro no campo 'ESTABELECIMENTO' (EC).
3. Observar que nenhuma transação é exibida e a mensagem de erro aparece.

Com o filtro de 'EC' aplicado, as transações eram exibidas corretamente.

## Causa raiz
Não informado explicitamente no ticket, mas infere-se que a consulta de transações no backend, acionada pela interface do usuário na ausência de um filtro de Estabelecimento Comercial (EC), resultava em um conjunto de dados vazio ou em um erro silencioso. Este comportamento implicava que o filtro de EC era mandatório para a recuperação de qualquer transação, impedindo a visualização padrão consolidada para o cliente.

## Solução
A solução foi implementada para ajustar a lógica de consulta no backend, permitindo que as transações sejam carregadas e exibidas corretamente na tela de visualização, mesmo quando o filtro de 'Estabelecimento Comercial' (EC) não é explicitamente aplicado pelo usuário. Esta mudança garante que a visualização padrão do cliente não seja bloqueada pela ausência de um filtro opcional.

Foi referenciado no ticket que a tarefa já havia sido executada em uma demanda DSMM anterior (DSMM-63).

## Como validar
1. Acessar a tela de visualização de transações no BackOffice.
2. **Não** aplicar nenhum filtro no campo 'ESTABELECIMENTO' (EC).
3. Confirmar que as transações são exibidas na lista, e os valores de 'Valor Bruto', 'Taxa Administrativa', 'Custo Antecipação' e 'Valor Líquido' são apresentados corretamente, e a mensagem de erro não é mais exibida.

## Se acontecer de novo
> [!tip] Como reconhecer e diagnosticar
Sinais: O principal sintoma é a mensagem 'Não há recebíveis no período solicitado, verifique os filtros e tente novamente.' sendo exibida na tela de visualização de transações quando nenhum filtro de Estabelecimento Comercial (EC) é aplicado, e os valores totais aparecendo como zero.

O que verificar primeiro:
- **Logs do BackOffice:** Verifique os logs do serviço que atende o endpoint `/api/v3/transacoes` (provavelmente `api-registradora` ou similar) por erros ou mensagens relacionadas a consultas de banco de dados ou filtros. Procure por mensagens de erro que possam indicar um problema com a construção da query.
- **Comportamento da API:** Se possível, teste o endpoint `/api/v3/transacoes` diretamente sem o parâmetro de filtro de EC para observar o retorno do backend.
- **Configurações:** Verifique se alguma configuração recente foi alterada que possa ter reintroduzido a obrigatoriedade de filtros para as consultas de transações.

## Referências
- PRs: Não informado no ticket.
- Notas relacionadas: [[BackOffice Subacquirer__bo-modulo-transacoes]]

## Ocorrências

### DSMM-66 · 2026-05-28 · Breno Martins
Primeira ocorrência: deu origem a esta nota. [Ticket](https://SEU-SITE.atlassian.net/browse/DSMM-66)
