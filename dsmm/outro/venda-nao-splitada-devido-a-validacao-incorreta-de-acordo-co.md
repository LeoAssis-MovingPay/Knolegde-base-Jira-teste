---
title: "Venda não splitada devido a validação incorreta de acordo comercial no Split Pós-Venda"
tags: ["dsmm","bug","outro","split","pos-venda","acordo-comercial","gateway","software-express","liquidacao"]
created: 2026-11-17
updated: 2026-11-17
tickets: ["DSMM-85"]
sistema: "Outro"
tipo: bug
pr: ""
---

# 🐛 Venda não splitada devido a validação incorreta de acordo comercial no Split Pós-Venda

> [!summary] Resumo
> A venda do EC 1098793 não estava sendo splitada conforme regra configurada no Console, mesmo após tentativas de re-cadastro. A causa foi uma validação incompleta do acordo comercial no fluxo de split pós-venda, onde o `merchants_id` do estabelecimento não era explicitamente considerado. A correção envolveu ajustar o payload da chamada de validação para incluir o `merchants_id`.

## Contexto
O sistema Console permite o cadastro de regras de split para estabelecimentos. No entanto, o processamento efetivo dessas regras ocorre no Gateway/API, que coordena os fluxos de `DivisaoCaptura` (quando o payload já contém os splits) e `DivisaoPosVenda` (para regras configuradas via Console). A funcionalidade em questão, `DivisaoPosVenda`, é responsável por aplicar as divisões financeiras com base nas regras de split pós-venda. A lambda `[[Registradora__lambda-registradora-contrato-processa-efeito]]` atua posteriormente no fluxo de pagamento, processando efeitos de contrato por arranjo de pagamento, mas não diretamente na lógica inicial de split.

## Sintoma
1.  O cliente DELTAPAG informou que, mesmo com uma regra de split cadastrada e ativa no Console para o EC 1098793, vendas de teste (ex: NSU 000540001562) não eram splitadas.
2.  O fluxo de split não era aplicado corretamente, resultando na transação permanecendo sem a divisão entre os recebedores configurados.
3.  Tentativas de excluir e recadastrar a regra no Console não resolveram o problema.

## Causa raiz
(Inferida da solução)
O fluxo de Split Pós-Venda (`DivisaoPosVenda`) no Gateway/API realizava uma validação do acordo comercial (`AcordoComercial.Validar`) sem incluir explicitamente o `merchants_id` do estabelecimento no payload. Embora o `rates_id` fosse usado como chave inicial, a ausência do `merchants_id` completo no contexto da validação impedia que o acordo comercial correto fosse selecionado ou aplicado, resultando na falha do split.
Trecho de código (conceitual, adaptado da descrição da solução):
```javascript
// Antes
AcordoComercial.Validar(payloadTransacao);

// Depois
AcordoComercial.Validar({ ...payloadTransacao, merchants_id: estabelecimento.id });
```

## Solução
Ajuste na validação do acordo comercial no fluxo de `DivisaoPosVenda` no repositório `API_GATEWAY`.
*   **Repositório/PR:** `movingpay/API_GATEWAY` - PR https://github.com/movingpay/API_GATEWAY/pul... (link truncado)
*   **Descrição da Mudança:** A chamada ao método `AcordoComercial.Validar` dentro de `app/Models/Splits/DivisaoPosVenda/index.js` foi modificada para incluir o `merchants_id` do estabelecimento no payload enviado.
*   **Números de antes/depois:** Não informado no ticket.

## Como validar
1.  Acessar o Console da DELTAPAG.
2.  Localizar o EC 1098793.
3.  Validar que existe uma regra de split cadastrada e ativa para esse EC.
4.  Processar uma nova venda de teste para o EC 1098793.
5.  Verificar que a transação é splitada corretamente entre os recebedores configurados.

## Se acontecer de novo
> [!tip] Como reconhecer e diagnosticar
*   **Sinais:** Vendas realizadas com regras de split configuradas no Console que não são efetivadas. Mensagens de erro ou logs relacionados a falhas na `DivisaoPosVenda` ou `AcordoComercial.Validar` no Gateway/API.
*   **Verificar primeiro:**
    1.  Confirmar no Console se a regra de split para o EC está ativa e corretamente configurada.
    2.  Verificar os logs do Gateway/API, especificamente no fluxo de `DivisaoPosVenda` em `app/Models/Splits/DivisaoPosVenda/index.js`, para identificar se a validação do acordo comercial está sendo realizada e com quais parâmetros.
    3.  Consultar os pontos de referência mencionados por Breno Martins para entender o fluxo de split (`Gateway/API/app/Models/Splits/DivisaoPosVenda/index.js`, `Gateway/API/app/Jobs/Internal/TR_SPLIT_PROCESS.js`).
*   **Prevenção:** Garantir que todas as chamadas de validação de acordos comerciais em fluxos críticos de liquidação recebam o contexto completo do estabelecimento, incluindo `merchants_id`, para evitar erros de contexto.

## Referências
*   PR: https://github.com/movingpay/API_GATEWAY/pul... (link truncado)
*   Notas relacionadas: `[[Registradora__lambda-registradora-contrato-processa-efeito]]`

## Ocorrências

### DSMM-85 · 2026-06-08 · Richael Fernando Nunes
Primeira ocorrência: deu origem a esta nota. [Ticket](https://SEU-SITE.atlassian.net/browse/DSMM-85)
