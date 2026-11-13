# Guia: base de conhecimento DSMM com n8n

Versão 2 (13/11/2026). Substitui a versão anterior.

Objetivo: quando um DSMM é resolvido no Jira, uma IA gera a nota de resolução (.md). O responsável pelo ticket aprova a nota no Slack, e ela é publicada no GitHub, de onde vai para o Obsidian.

---

## 0. Como funciona (resumo)

```
WORKFLOW A — "DSMM - Coletor"            (a cada 10 min)
  Schedule → Jira: busca DSMMs resolvidos sem a label kb-processado
           → Jira: adiciona a label → chama o workflow B (1 vez por ticket)

WORKFLOW B — "DSMM - Gerar nota"         (1 execução por ticket)
  Início (recebe a chave) → Jira: ticket + comentários → GitHub: PR do ticket
  → Code: monta contexto e mascara dados sensíveis → IA → vale documentar?
  → Code: monta o .md → Slack: acha o responsável → Slack: pede aprovação (espera até 48h)
       ├─ Aprovar  → GitHub: salva a nota → comenta o link no Jira → avisa no Slack
       ├─ Ajustar  → volta para a IA com o comentário (no máximo 2 vezes)
       ├─ Rejeitar → comenta no Jira e encerra
       └─ Sem resposta → avisa o tech lead

WORKFLOW C — "DSMM - Erros"
  Error Trigger → avisa no Slack quando A ou B falhar
```

Por que esse desenho:

| Decisão | Motivo |
|---|---|
| O n8n **consulta** o Jira (polling), em vez de o Jira chamar o n8n | O n8n está só na rede local, sem DNS e com certificado próprio. Ele só faz conexões de saída, então não é preciso expor nada na internet. |
| Filtro na JQL | Só chegam tickets que valem documentar. |
| A label `kb-processado` é marcada antes de gerar a nota | O ticket não é pego de novo enquanto espera aprovação. Para reprocessar, basta tirar a label. |
| Dois workflows | Cada ticket espera a aprovação sozinho, sem travar os outros. |
| Uma única chamada de IA, com resposta em JSON | Mais barato e previsível. Ticket, datas, links e responsável vêm do Jira por código, então a IA não tem como inventar esses dados. |
| Nome do arquivo = chave do ticket | Se o ticket for reaberto e resolvido de novo, a nota é atualizada em vez de duplicada. |
| O índice é gerado por uma GitHub Action | O n8n não precisa cuidar disso. |

---

## 1. Preparação

### 1.1 Repositório GitHub
A pasta `base-conhecimento-dsmm` já está na sua Área de Trabalho. Publique-a pelo GitHub Desktop como repositório **privado**.

```
base-conhecimento-dsmm/
├── dsmm/<sistema>/DSMM-123.md   ← notas (registradora, cerc, b3, tag, slc, bs2,
│                                   manager, backoffice, iam, outro)
├── templates/nota-dsmm.md       ← modelo da nota
├── n8n/prompts/                 ← prompts da IA (mantenha igual ao do n8n)
├── n8n/workflows/               ← exports dos workflows (sem credenciais)
├── scripts/gerar_indice.py      ← gera o índice do README
├── .github/workflows/indice.yml ← roda o script a cada nota nova
└── docs/                        ← este guia + como contribuir
```

No GitHub: **Settings → Actions → General → Workflow permissions → Read and write**. Sem isso, a Action não consegue atualizar o índice.

No Obsidian: instale o plugin **Obsidian Git** apontando para o repositório. Os links `[[CERC]]` nas notas ligam com as notas de mesmo nome do vault.

### 1.2 Servidor n8n
O n8n roda self-hosted, na rede local, com HTTPS por certificado próprio.

Variáveis de ambiente (Docker):

| Variável | Valor | Para quê |
|---|---|---|
| `WEBHOOK_URL` | `https://<IP-do-n8n>:<porta>/` | Base dos links de aprovação enviados no Slack. Precisa ser o endereço que os devs abrem no navegador. |
| `GENERIC_TIMEZONE` | `America/Sao_Paulo` | Horário do agendamento |
| `N8N_ENCRYPTION_KEY` | segredo fixo, guardado no Vaultwarden | Sem ela, as credenciais se perdem ao recriar o container |
| `EXECUTIONS_DATA_PRUNE` / `EXECUTIONS_DATA_MAX_AGE` | `true` / `168` | Apaga o histórico de execuções depois de 7 dias |
| `DB_TYPE=postgresdb` (+ `DB_POSTGRESDB_*`) | recomendado | Execuções em espera ficam mais seguras no Postgres. SQLite funciona para pouco volume. |

Rede e certificado:
- Os links de aprovação abrem o n8n pela rede local, então **quem aprova precisa estar no escritório ou na VPN**.
- Para não aparecer aviso de certificado: o certificado precisa ter o **IP no SAN** (não só no CN). Distribua o certificado (ou a CA que o assinou) via GPO no AD, em *Computer Configuration → Policies → Windows Settings → Security Settings → Public Key Policies → Trusted Root Certification Authorities*. Chrome e Edge usam esse repositório.
- O n8n precisa de **saída** para `*.atlassian.net`, `slack.com`, `api.github.com` e a API da IA (ex.: `api.anthropic.com`).

### 1.3 Credenciais (n8n → Credentials → Add)

| Credencial no n8n | Como obter | Permissão mínima |
|---|---|---|
| **Jira SW Cloud API** | Use um usuário de serviço. Em id.atlassian.com → Security → **API tokens** → Create. No n8n: e-mail + token + domínio `https://SEU-SITE.atlassian.net` | Ler, comentar e **editar** (para a label) no projeto DSMM |
| **Slack API** | api.slack.com/apps → *Create New App* → *From scratch*. Em **OAuth & Permissions → Bot Token Scopes**, adicione `chat:write`, `im:write`, `users:read`, `users:read.email`. Depois *Install to Workspace* e copie o token `xoxb-…`. Em **App Home**, habilite a *Messages Tab*. | — |
| **GitHub API** | GitHub → Settings → Developer settings → **Fine-grained tokens** | `base-conhecimento-dsmm`: Contents **Read & Write**. Repositórios de código: Contents e Pull requests **Read** (para achar o PR). |
| **Anthropic** (ou outro LLM) | Console da API → API key | — |

O formulário de aprovação do Slack abre por link para o n8n, então **não** é preciso configurar Interactivity no app do Slack.

---

## 2. Workflow B: "DSMM - Gerar nota"

Monte este primeiro, porque o workflow A chama ele. Os nomes em **negrito** são os nomes dos nós; o código se refere a eles, então use exatamente esses.

### B1. **Início**: *When Executed by Another Workflow*
- Input data mode: **Define using fields below** → campo `key` (String).
- **Para testar:** clique em **Pin data** (ícone de alfinete), cole `{"key": "DSMM-123"}` com um ticket real resolvido e use **Execute workflow**. Todos os nós seguintes podem ser testados com esse dado fixo.

### B2. **Jira - Ticket**: Jira Software → Issue → Get
- Issue Key: `{{ $json.key }}`

### B3. **Jira - Comentários**: Jira Software → Issue Comment → Get Many
- Issue Key: `{{ $('Início').item.json.key }}` · Return All: on
- Settings → **Always Output Data**: on (o ticket pode não ter comentários)

### B4. **GitHub - Busca PR**: HTTP Request (opcional, mas melhora muito a causa raiz)
Funciona se o time puser `DSMM-123` no título do PR ou no nome da branch. Vale combinar isso com os devs.
- GET `https://api.github.com/search/issues`
- Authentication: Predefined → **GitHub API**
- Query Parameter `q` = `{{ $('Início').item.json.key }} type:pr org:movingpay`
- Settings → **On Error: Continue** · **Always Output Data**: on

### B5. **GitHub - Arquivos do PR**: HTTP Request
- GET `{{ $json.items[0].pull_request.url }}/files` · Query `per_page` = `50`
- Authentication: **GitHub API**
- Settings → **On Error: Continue** · **Always Output Data**: on

### B6. **Monta contexto**: Code (Run Once for All Items)
Junta tudo, **mascara dados sensíveis** e corta textos longos antes de mandar para a IA. Troque `SEU-SITE`.

```js
const JIRA = 'https://SEU-SITE.atlassian.net';
const issue = $('Jira - Ticket').first().json;
const f = issue.fields;
const comments = $('Jira - Comentários').all().map(i => i.json).filter(c => c.body);
let prFiles = [], prUrl = '';
try { prFiles = $('GitHub - Arquivos do PR').all().map(i => i.json).filter(x => x.filename); } catch (e) {}
try { prUrl = $('GitHub - Busca PR').first().json.items?.[0]?.html_url || ''; } catch (e) {}

// Jira Cloud devolve descrição e comentários em ADF (JSON) → texto puro
const adf = n => !n ? '' : typeof n === 'string' ? n
  : n.type === 'text' ? n.text
  : (n.content || []).map(adf).join(['paragraph','heading','listItem','codeBlock'].includes(n.type) ? '\n' : '');

// Mascarar dados sensíveis (primeira barreira; acrescente padrões próprios se precisar)
const mask = t => (t || '')
  .replace(/\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}\b/g, '[CNPJ]')
  .replace(/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g, '[CPF]')
  .replace(/\b(?:\d[ -]?){13,19}\b/g, '[CARTAO]')
  .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[EMAIL]')
  .replace(/\b(bearer|token|senha|password|secret|apikey|api_key)\b\s*[:=]?\s*\S+/gi, '$1 [REMOVIDO]');

const cut = (t, n) => t.length > n ? t.slice(0, n) + '\n…[truncado]' : t;

const coments = comments.slice(-15)
  .map(c => `- ${c.author?.displayName} (${(c.created || '').slice(0, 10)}): ${cut(mask(adf(c.body)), 1500)}`)
  .join('\n');
const diff = cut(mask(prFiles.map(p => `### ${p.filename}\n${p.patch || ''}`).join('\n')), 6000);

const contexto = `TICKET: ${issue.key} — ${mask(f.summary)}
TIPO JIRA: ${f.issuetype?.name}
COMPONENTES: ${(f.components || []).map(c => c.name).join(', ')}
LABELS: ${(f.labels || []).join(', ')}

DESCRIÇÃO:
${cut(mask(adf(f.description)), 4000)}

COMENTÁRIOS (mais recentes):
${coments || '(sem comentários)'}

ALTERAÇÕES NO PR:
${diff || '(PR não encontrado)'}`;

return [{ json: {
  key: issue.key,
  url: `${JIRA}/browse/${issue.key}`,
  responsavel_email: f.assignee?.emailAddress || '',
  responsavel_nome: f.assignee?.displayName || '',
  resolvido_em: (f.resolutiondate || new Date().toISOString()).slice(0, 10),
  pr_url: prUrl,
  contexto,
  feedback: ''
}}];
```

### B7. **IA**: Basic LLM Chain
- Sub-nó **Chat Model**: Anthropic Chat Model (ex.: Claude Sonnet), temperatura 0.2.
- Ligue **Require Specific Output Format** e conecte um **Structured Output Parser** usando o exemplo de `n8n/prompts/output-schema.json`:

```json
{
  "documentar": true, "motivo": "",
  "sistema": "CERC", "tipo": "bug",
  "titulo": "Timeout no envio de agenda para a CERC",
  "tags": ["timeout", "agenda", "retry"],
  "sintoma": "...", "causa_raiz": "...", "solucao": "...",
  "como_validar": "...", "observacoes": "..."
}
```

- **System message** (o mesmo texto de `n8n/prompts/system.md`):
```
Você documenta a resolução de chamados DSMM (bugs e melhorias de software) da MovingPay
para uma base de conhecimento usada por desenvolvedores.

Regras:
- Use somente o que está no contexto. Não invente. Se a causa raiz não estiver clara, escreva
  "Não identificada no ticket".
- Seja técnico e direto: nomes de serviços, endpoints, tabelas, mensagens de erro, configurações.
- Nunca inclua dados de cliente, CPF/CNPJ, cartões, e-mails, tokens ou senhas.
- "documentar" = false se o ticket não ensina nada reutilizável (ex.: ajuste de texto, chamado
  sem solução técnica, duplicado). Explique em "motivo".
- "sistema": um de [Registradora, CERC, B3, TAG, SLC, BS2, Manager, BackOffice, IAM, Outro].
- "tipo": "bug" ou "melhoria". Para melhoria, "causa_raiz" = motivação da mudança.
- Escreva em português, em Markdown dentro de cada campo (listas e `código` são permitidos).
```
- **Prompt (user)**, definido abaixo (*Define below*):
```
{{ $json.contexto }}

{{ $json.feedback ? 'AJUSTES PEDIDOS PELO RESPONSÁVEL (aplique na nova versão):\n' + $json.feedback : '' }}
```

### B8. **Documentar?**: IF
- Condição: `{{ $json.output.documentar }}` → Boolean → *is true*.
- Saída **false**: opcionalmente, um Jira → Issue Comment → Add com o texto `Sem nota de resolução: {{ $json.output.motivo }}`.

### B9. **Monta MD**: Code (Run Once for All Items)
```js
const c = $('Monta contexto').first().json;
const r = $input.first().json.output;
const pasta = (r.sistema || 'outro').toLowerCase().replace(/\s+/g, '-');
const md = `---
ticket: ${c.key}
titulo: "${r.titulo.replace(/"/g, "'")}"
sistema: ${r.sistema}
tipo: ${r.tipo}
tags: [${(r.tags || []).map(t => `"${t}"`).join(', ')}]
responsavel: ${c.responsavel_nome}
resolvido_em: ${c.resolvido_em}
jira: ${c.url}
pr: ${c.pr_url}
---

# ${c.key} — ${r.titulo}

Sistema: [[${r.sistema}]]

## Sintoma
${r.sintoma}

## Causa raiz
${r.causa_raiz}

## Solução
${r.solucao}

## Como validar
${r.como_validar}

## Observações
${r.observacoes || '-'}
`;
return [{ json: { ...c, ...r, md, caminho: `dsmm/${pasta}/${c.key}.md` } }];
```

### B10. **Slack - Usuário**: HTTP Request
- GET `https://slack.com/api/users.lookupByEmail` · Query `email` = `{{ $json.responsavel_email }}`
- Authentication: Predefined → **Slack API**
- O ID do usuário fica em `{{ $json.user.id }}`.
- ⚠ O Jira Cloud pode esconder o e-mail do responsável (privacidade do perfil). Nesse caso a resposta vem com `ok: false`. Coloque um IF `{{ $json.ok }}`: se for falso, mande a aprovação para um canal (ex.: `#dsmm-notas`) em vez da DM, ou use uma Data Table no n8n que liga o usuário do Jira ao usuário do Slack.

### B11. **Slack - Aprovação**: Slack → Message → Send and Wait for Response
- Send Message To: **User** → By ID → `{{ $json.user.id }}`
- Message:
~~~
📚 *Nota de resolução para revisar: {{ $('Monta MD').item.json.key }}*
{{ $('Monta MD').item.json.titulo }} · {{ $('Monta MD').item.json.sistema }} · <{{ $('Monta MD').item.json.url }}|abrir ticket>

```{{ $('Monta MD').item.json.md.slice(0, 2500) }}```
~~~
- Response Type: **Custom Form** → campos:
  1. `Decisão`: Dropdown com `Aprovar`, `Ajustar`, `Rejeitar` (obrigatório)
  2. `Observação`: Textarea (o que ajustar)
- Options → **Limit Wait Time**: 48 horas · **Message Button Label**: `Revisar nota`
- O dev clica no botão, abre o formulário no n8n pela rede local e responde. O workflow continua sozinho.

### B12. **Decisão**: Switch (Rules)
- Valor: `{{ $json.data['Decisão'] }}`. Confira o nome exato do campo na saída do B11 no primeiro teste.
- Regras: `Aprovar` → B13 · `Ajustar` → B16 · `Rejeitar` → B17
- Options → **Fallback Output: Extra Output** → B18 (sem resposta em 48h)

### B13. Salvar no GitHub
1. **GitHub - Existe?**: GitHub → File → Get
   - Owner: `movingpay` · Repository: `base-conhecimento-dsmm` · File Path: `{{ $('Monta MD').item.json.caminho }}`
   - Settings → **On Error: Continue (using error output)**
2. Saída de **sucesso** (o arquivo já existe) → **GitHub → File → Edit**. Saída de **erro** (o arquivo não existe) → **GitHub → File → Create**. Os dois com:
   - File Path: `{{ $('Monta MD').item.json.caminho }}`
   - File Content: `{{ $('Monta MD').item.json.md }}`
   - Commit Message: `docs(dsmm): {{ $('Monta MD').item.json.key }} — {{ $('Monta MD').item.json.titulo }}`

### B14. Comentário no Jira: Jira Software → Issue Comment → Add
- Issue Key: `{{ $('Monta MD').item.json.key }}`
- Texto: `📚 Nota de resolução publicada: https://github.com/movingpay/base-conhecimento-dsmm/blob/main/{{ $('Monta MD').item.json.caminho }}`

### B15. Confirmação: Slack → Message → Send
- Para o usuário `{{ $('Slack - Usuário').item.json.user.id }}`: `✅ Nota {{ $('Monta MD').item.json.key }} publicada.`

### B16. **Ajuste**: Edit Fields (Set) → IF → volta para a IA
- Campos:
  - `contexto` = `{{ $('Monta contexto').item.json.contexto }}`
  - `feedback` = `{{ $('Slack - Aprovação').item.json.data['Observação'] }}`
  - `tentativa` = `{{ $runIndex + 1 }}`
- IF `tentativa <= 2` → liga de volta na entrada do nó **IA** (B7).
- Se passar de 2: Slack para o dev → "Ajuste direto no GitHub/Obsidian: {{ caminho }}".

### B17. Rejeitar: Jira → Issue Comment → Add (opcional)
- `Nota de resolução rejeitada pelo responsável.` e o fluxo encerra.

### B18. Sem resposta: Slack → Message → Send
- Para o tech lead ou o canal `#dsmm-notas`: `⏰ {{ $('Monta MD').item.json.key }} está sem revisão há 48h.`

---

## 3. Workflow A: "DSMM - Coletor"

### A1. Schedule Trigger
- A cada **10 minutos**. Para rodar só em horário comercial, use Cron: `*/10 8-19 * * 1-5`.

### A2. **Jira - Buscar resolvidos**: Jira Software → Issue → Get Many
- Return All: on · Options → **JQL**:
```
project = DSMM
AND issuetype in (Bug, Melhoria)
AND statusCategory = Done
AND resolution not in (Duplicate, "Won't Do", "Cannot Reproduce")
AND resolved >= -7d
AND (labels is EMPTY OR labels not in (kb-processado))
```
- Teste a JQL antes na busca avançada do Jira e ajuste os nomes de tipo e resolução.
- O `labels is EMPTY` é necessário porque `labels not in (...)` sozinho ignora os tickets sem nenhuma label.
- `resolved >= -7d` impede que a primeira execução processe o histórico todo. Para gerar notas de tickets antigos, aumente esse prazo temporariamente.

### A3. **Jira - Marca label**: HTTP Request
- PUT `https://SEU-SITE.atlassian.net/rest/api/3/issue/{{ $json.key }}`
- Authentication: Predefined → **Jira SW Cloud API**
- Body (JSON): `{"update":{"labels":[{"add":"kb-processado"}]}}`
- Use HTTP em vez do nó Jira "Update", porque o Update substitui todas as labels.

### A4. Execute Workflow (Execute Sub-workflow)
- Source: **Database** → **DSMM - Gerar nota**
- Mode: **Run once for each item**
- Workflow Inputs → `key` = `{{ $('Jira - Buscar resolvidos').item.json.key }}`
- Options → **Wait For Sub-Workflow Completion: off**

**Ative** o workflow A (Active/Publish). O B não precisa ser ativado: ele é chamado pelo A.

---

## 4. Workflow C: "DSMM - Erros"
- **Error Trigger** → Slack → Message → Send, para você ou para um canal de alertas:
  `❌ {{ $json.workflow.name }} falhou: {{ $json.execution.error.message }} — {{ $json.execution.url }}`
- Nos workflows A e B, vá em **Settings** e configure:
  - **Error Workflow** = DSMM - Erros
  - **Save successful production executions** = **No** (as execuções guardam dados dos tickets)

---

## 5. Testes e implantação

1. **Workflow B isolado:** fixe `{"key":"DSMM-xxx"}` no nó Início e execute com 3 a 5 tickets antigos e variados. Ajuste o prompt até as notas ficarem boas. Mantenha `n8n/prompts/` igual ao que está no n8n.
2. **Aprovação:** teste com você mesmo como responsável os três caminhos: Aprovar, Ajustar e Rejeitar.
3. **Workflow A:** rode a JQL no Jira, depois execute o A manualmente uma vez e confira se as labels foram aplicadas.
4. **Piloto:** ative o fluxo para um squad por 2 a 3 semanas. Meça quantas notas foram aprovadas de primeira e quantas pediram ajuste.
5. **Versionar:** exporte os workflows (⋯ → Download) para `n8n/workflows/` no repositório. O export não leva credenciais.
6. Abra o fluxo para todos os squads.

---

## 6. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| O workflow A não acha nenhum ticket | Nome de tipo, status ou resolução diferente na JQL | Testar a JQL na busca do Jira |
| `Slack - Usuário` retorna `ok: false` | O Jira não expôs o e-mail do responsável | Usar o canal como alternativa ou uma tabela Jira → Slack |
| O link de aprovação não abre | Dev fora da rede/VPN ou `WEBHOOK_URL` errado | Conferir a variável e o acesso à rede |
| Aviso de certificado no navegador | Certificado não confiável ou sem o IP no SAN | Reemitir com SAN e distribuir via GPO |
| GitHub retorna 404 | O token não tem acesso ao repositório | Ajustar o fine-grained token |
| O PR nunca é encontrado | A chave do ticket não está no título do PR ou na branch | Combinar a convenção com os devs (ou ignorar: o B4 é opcional) |
| Preciso gerar a nota de um ticket de novo | — | Tirar a label `kb-processado` do ticket; ele entra na próxima rodada |

---

## 7. Custo e manutenção
- Uma chamada de IA por ticket (cerca de 5 a 10 mil tokens de entrada) custa centavos.
- Revisar de tempos em tempos: lista de sistemas (no prompt e nas pastas do repositório), validade dos tokens (Jira, GitHub) e o certificado do n8n.
- **Futuro (opcional):** se quiser a nota em tempo real, um **Cloudflare Tunnel** publicando só `/webhook/dsmm-resolvido` permite que o Jira Automation chame o n8n direto, substituindo o workflow A. O workflow B continua igual.
