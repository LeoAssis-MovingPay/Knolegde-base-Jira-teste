---
title: "Transações pagas não aparecem na conciliação de recebíveis sem filtro de EC"
tags: ["dsmm","bug","manager","conciliacao","recebiveis","ec","filtro","api-registradora"]
created: 2026-11-17
updated: 2026-11-17
tickets: ["DSMM-71"]
sistema: "Manager"
tipo: bug
pr: ""
---

# 🐛 Transações pagas não aparecem na conciliação de recebíveis sem filtro de EC

> [!summary] Resumo
> A tela de conciliação de recebíveis não exibia transações pagas por padrão, mostrando uma mensagem de que não havia recebíveis. Isso ocorria porque a consulta de dados exigia a aplicação manual de um filtro de Estabelecimento Comercial (EC).

## Contexto
Esta nota refere-se à tela de **Conciliação de Recebíveis** no [[Manager]] (rota `/cerc/schedules`), que é responsável por exibir a agenda consolidada de recebíveis e transações pagas. Os dados são processados pelo serviço `ecs-image-cerc-ap-009` e persistidos no `MongoDB` na coleção `AcquirerConciliation`, sendo expostos ao Manager através da `api-registradora`.

Para mais detalhes sobre o fluxo, consulte [[MovingPay__CERC__Agenda de Recebíveis - Fluxo e Estrutura]].

## Sintoma
Ao acessar a tela de Conciliação de Recebíveis, o usuário encontrava a seguinte situação:

1.  A mensagem "Não há recebíveis no período solicitado, verifique os filtros e tente novamente" era exibida por padrão.
2.  Os valores totais (TPV, MDR, etc.) mostravam R$ 0,00.
3.  Para que as informações fossem carregadas, era necessário aplicar manualmente um filtro de Estabelecimento Comercial (EC).

### Como reproduzir
1.  Acessar a tela de conciliação de recebíveis no Manager.
2.  Não aplicar nenhum filtro de EC.
3.  Observar a mensagem de erro ou a ausência de dados na lista de transações e nos valores totais.
4.  Aplicar um filtro de EC válido.
5.  Observar que as transações e valores são exibidos corretamente.

## Causa raiz
Não informado explicitamente no ticket DSMM-71. 

Inferido: A lógica de consulta dos recebíveis e transações na `api-registradora`, que alimenta a tela de conciliação, exigia um filtro de Estabelecimento Comercial (EC) como parâmetro obrigatório. Quando a tela era carregada sem um EC selecionado, a consulta falhava ou retornava um conjunto de dados vazio, resultando na mensagem de "não há recebíveis" e valores zerados.

## Solução
A demanda foi refinada e desenvolvida anteriormente sob o ticket DSMM-63, que implementou a exibição padrão das transações na tela de conciliação de recebíveis sem a necessidade de um filtro inicial de EC. A correção provavelmente envolveu o ajuste da lógica de consulta no backend (`api-registradora`) para lidar com o cenário sem filtro de EC, possivelmente aplicando um filtro padrão ou buscando todos os dados do cliente subjacente.

**PRs relacionados:**
Não informado no ticket DSMM-71. O PR original estaria associado a https://movingpay.atlassian.net/browse/DSMM-63.

## Como validar
1.  Acessar a tela de Conciliação de Recebíveis no Manager.
2.  Verificar se a lista de transações pagas e os valores totais (TPV, MDR, etc.) são carregados automaticamente ao abrir a tela, sem a necessidade de aplicar qualquer filtro de EC.
3.  Confirmar que a funcionalidade de filtrar por EC continua operando corretamente, atualizando os dados conforme o filtro aplicado.

## Se acontecer de novo
> [!tip] Como reconhecer e diagnosticar
*   **Sinais:** Usuários reportam a ausência de transações na tela de conciliação de recebíveis ou valores zerados, acompanhados da mensagem "Não há recebíveis no período solicitado, verifique os filtros e tente novamente", mesmo havendo dados esperados.
*   **Verificar primeiro:**
    *   Consulte os logs da `api-registradora` para chamadas aos endpoints de conciliação (e.g., `/api/cerc/ap009/conciliations`) no momento em que a tela é acessada sem filtro.
    *   Inspecione as queries executadas no `MongoDB` (coleção `AcquirerConciliation`) para entender se algum filtro mandatório de EC está sendo aplicado ou se a query está retornando vazio de forma inesperada.
    *   Verifique se há alguma alteração recente na lógica de filtragem ou nos parâmetros esperados para a consulta de recebíveis.
*   **Prevenção:** Garantir que as consultas de dados no backend para a tela de conciliação de recebíveis sempre considerem um comportamento padrão robusto ou um fallback adequado quando nenhum filtro de EC é fornecido pela interface do usuário.

## Referências
- [[MovingPay__CERC__Agenda de Recebíveis - Fluxo e Estrutura]]
- Demanda original: https://movingpay.atlassian.net/browse/DSMM-63

## Ocorrências

### DSMM-71 · 2026-05-28 · Breno Martins
Primeira ocorrência: deu origem a esta nota. [Ticket](https://SEU-SITE.atlassian.net/browse/DSMM-71)
