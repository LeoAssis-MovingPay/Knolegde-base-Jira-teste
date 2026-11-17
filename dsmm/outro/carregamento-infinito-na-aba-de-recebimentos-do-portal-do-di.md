---
title: "Carregamento infinito na aba de Recebimentos do Portal do Distribuidor"
tags: ["dsmm","bug","outro","portal","distribuidor","recebimentos","carregamento","frontend"]
created: 2026-11-17
updated: 2026-11-17
tickets: ["DSMM-34"]
sistema: "Outro"
tipo: bug
pr: ""
---

# 🐛 Carregamento infinito na aba de Recebimentos do Portal do Distribuidor

> [!summary] Resumo
> Um problema causava um estado de carregamento infinito na aba de Recebimentos do Portal do Distribuidor. A causa raiz foi identificada e a correção foi implementada através da demanda DSMM-63, resolvendo o comportamento.

## Contexto
O Portal do Distribuidor é uma aplicação web que permite aos distribuidores da MovingPay acessarem informações e funcionalidades relacionadas aos seus negócios. A aba de "Recebimentos" neste portal exibe dados consolidados de fluxos financeiros. Embora não detalhado neste ticket, é provável que esta funcionalidade consuma serviços de backend similares aos usados pela [[MovingPay__CERC__Agenda de Recebíveis - Fluxo e Estrutura]] no Manager, que interage com a `api-registradora` e coleções `MongoDB` como `AcquirerConciliation`. A autenticação para acesso à `api-registradora` é gerenciada pelo [[Registradora__lambda-authorizer-api-registradora-movingpay]].

## Sintoma
Usuários do Portal do Distribuidor reportavam que, ao acessar a aba de "Recebimentos", a tela ficava em um estado de carregamento infinito, impedindo a visualização dos dados.

### Como Reproduzir
1.  Acessar o PORTAL DO DISTRIBUIDOR.
2.  Navegar até a aba de "Recebimentos".
3.  Observar que a tela permanece em um estado de carregamento infinito.

## Causa raiz
Não informado no ticket DSMM-34. A resolução foi tratada por um ticket relacionado, DSMM-63, que implementou a correção para o problema de carregamento.

## Solução
A correção foi desenvolvida e implementada em produção através da demanda DSMM-63 (https://movingpay.atlassian.net/browse/DSMM-63).

## Como validar
1.  Acessar o PORTAL DO DISTRIBUIDOR, preferencialmente utilizando as credenciais do distribuidor 1935 (AMERICAPAY).
2.  Navegar até a aba de "Recebimentos".
3.  Confirmar que a tela carrega corretamente e exibe os dados esperados.

## Se acontecer de novo
> [!tip] Como reconhecer e diagnosticar
Observe se a aba de "Recebimentos" no Portal do Distribuidor entra novamente em um estado de carregamento infinito ou apresenta lentidão excessiva. Para diagnosticar, verifique os logs do frontend do Portal do Distribuidor e, se aplicável, os logs da `api-registradora` para identificar erros nas chamadas relacionadas à obtenção de dados de recebíveis ou agenda. Falhas de autenticação ou autorização, gerenciadas pelo [[Registradora__lambda-authorizer-api-registradora-movingpay]], também podem causar esse tipo de sintoma ao impedir o acesso aos dados.

## Referências
-   DSMM-63: https://movingpay.atlassian.net/browse/DSMM-63
-   [[MovingPay__CERC__Agenda de Recebíveis - Fluxo e Estrutura]]
-   [[Registradora__lambda-authorizer-api-registradora-movingpay]]

## Ocorrências

### DSMM-34 · 2026-05-28 · Pedro Miguel Bonini de Cerqueira
Primeira ocorrência: deu origem a esta nota. [Ticket](https://SEU-SITE.atlassian.net/browse/DSMM-34)
