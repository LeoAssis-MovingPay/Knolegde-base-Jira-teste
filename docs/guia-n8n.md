# Guia: base de conhecimento DSMM com n8n

Versão 4 (16/11/2026). Notas com nome do problema; problema repetido atualiza a nota existente em vez de criar outra; menos tokens por ticket (pensado para API gratuita).

Objetivo: quando um DSMM é resolvido no Jira, uma IA gera a nota de resolução (.md). O responsável pelo ticket aprova a nota no Slack, e ela é publicada no GitHub, de onde vai para o Obsidian.

---

## 0. Como funciona (resumo)

```
WORKFLOW A — "DSMM - Coletor"            (a cada 10 min)
  Schedule → Jira: busca DSMMs resolvidos sem a label kb-processado
           → Jira: adiciona a label → chama o workflow B (1 vez por ticket)

WORKFLOW B — "DSMM - Gerar nota"         (1 execução por ticket)
  Início (recebe a chave) → Jira: ticket + comentários → GitHub: PR do ticket
  → GitHub: notas relacionadas da knowledge-base + indice.json das notas DSMM
  → Code: monta contexto, mascara dados e acha notas DSMM parecidas → tem comentários? (senão, para sem IA)
  → IA (1 chamada): nota nova OU adendo para uma nota existente
  → Code: monta o .md (novo arquivo ou nota existente + ocorrência)
  → Slack: acha o responsável → Slack: pede aprovação (espera até 48h)
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
| Nome do arquivo = nome do problema (`dsmm/<sistema>/<titulo-do-problema>.md`), tickets no cabeçalho | A nota é encontrada pelo assunto. Problema repetido vira uma nova **ocorrência** na mesma nota; ticket reprocessado substitui a própria ocorrência. |
| Notas parecidas achadas por código (`indice.json`) | A IA recebe só título e resumo de até 3 candidatas (~300 tokens), nunca o repositório inteiro. |
| O índice é gerado por uma GitHub Action | O n8n não precisa cuidar disso. |

---

## 1. Preparação

### 1.1 Repositório GitHub
A pasta `base-conhecimento-dsmm` já está na sua Área de Trabalho. Publique-a pelo GitHub Desktop como repositório **privado**.

```
base-conhecimento-dsmm/
├── dsmm/<sistema>/<problema>.md ← notas (registradora, cerc, b3, tag, slc, bs2,
│                                   manager, backoffice, console, iam, outro)
├── templates/nota-dsmm.md       ← modelo da nota
├── n8n/prompts/                 ← prompts da IA (mantenha igual ao do n8n)
├── n8n/workflows/               ← exports dos workflows (sem credenciais)
├── indice.json                  ← índice lido pelo n8n (gerado pela Action)
├── scripts/gerar_indice.py      ← gera o README e o indice.json
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
| **GitHub API** | GitHub → Settings → Developer settings → **Fine-grained tokens** (Resource owner: `movingpay`) | `base-conhecimento-dsmm`: Contents **Read & Write**. `knowledge-base`: Contents **Read**. Repositórios de código: Contents e Pull requests **Read** (para achar o PR). |
| **Anthropic** (ou outro LLM) | Console da API → API key | — |

O formulário de aprovação do Slack abre por link para o n8n, então **não** é preciso configurar Interactivity no app do Slack.

---

## 2. Workflow B: "DSMM - Gerar nota"

Monte este primeiro, porque o workflow A chama ele. Os nomes em **negrito** são os nomes dos nós; o código se refere a eles, então use exatamente esses.

Para buscar dados de nós anteriores, use `$('Nó').first().json...`, e não `.item` nem `$json`. O `$json` só vale para o nó imediatamente anterior. Cada execução do B trata um único ticket, então `first()` é seguro. Ele também continua funcionando depois do Switch, da espera no Slack e das saídas de erro, pontos em que `$json` passa a ser outra coisa (a resposta do formulário ou o erro).

> [!important] Execute Once
> No n8n, um nó roda **uma vez para cada item** que recebe. Depois do B3 chegam vários itens (um por comentário), e depois do B5, um por arquivo do PR. Por isso, em **B4, B5a e B5d**, ligue **Settings → Execute Once**. Sem isso, a busca do PR e a leitura do repositório se repetem dezenas de vezes.

### B1. **Início**: *When Executed by Another Workflow*
- Input data mode: **Define using fields below** → campo `key` (String).
- **Para testar:** clique em **Pin data** (ícone de alfinete), cole `{"key": "DSMM-123"}` com um ticket real resolvido e use **Execute workflow**. Todos os nós seguintes podem ser testados com esse dado fixo.

### B2. **Jira - Ticket**: Jira Software → Issue → Get
- Issue Key: `{{ $json.key }}`

### B3. **Jira - Comentários**: Jira Software → Issue Comment → Get Many
- Issue Key: `{{ $('Início').first().json.key }}` · Return All: on
- Settings → **Always Output Data**: on (o ticket pode não ter comentários)

### B4. **GitHub - Busca PR**: HTTP Request (opcional, mas melhora muito a causa raiz)
Funciona se o time puser `DSMM-123` no título do PR ou no nome da branch. Vale combinar isso com os devs.
- GET `https://api.github.com/search/issues`
- Authentication: Predefined → **GitHub API**
- Query Parameter `q` = `{{ $('Início').first().json.key }} type:pr org:movingpay`
- Settings → **Execute Once**: on · **On Error: Continue** · **Always Output Data**: on

### B5. **GitHub - Arquivos do PR**: HTTP Request
- GET `{{ $json.items[0].pull_request.url }}/files` · Query `per_page` = `50`
- Authentication: **GitHub API**
- Settings → **On Error: Continue** · **Always Output Data**: on

### B5a. **KB - Árvore**: HTTP Request (lista as notas da base de conhecimento)
A base técnica do Obsidian (`knowledge-base/`) é o repositório `movingpay/knowledge-base`. O n8n lê de lá as notas ligadas ao ticket, para a IA explicar o sistema e criar `[[links]]` para elas.
- GET `https://api.github.com/repos/movingpay/knowledge-base/git/trees/main?recursive=1`
- Authentication: Predefined → **GitHub API**. O token precisa de **Contents: Read** no repositório `knowledge-base`.
- Settings → **Execute Once**: on · **On Error: Continue** · **Always Output Data**: on

### B5b. **KB - Escolhe notas**: Code (Run Once for All Items)
Escolhe até 2 notas cujo nome combina com as palavras do ticket e com os repositórios citados nos PRs.
```js
const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const tokens = s => norm(s).split(/[^a-z0-9]+/).filter(t => t.length >= 4);
const stem = t => t.slice(0, 7);
const GEN = new Set(['readme','overview','modulo','fluxo','geral','integracoes','servicos','modulos','manager',
  'arquitetura','estrutura','lambda','registradora','image','task','events','api','ecs','subacquirer','backoffice']);

// texto do ticket: título + todos os textos/links da descrição e dos comentários
const issue = $('Jira - Ticket').first().json;
const bruto = JSON.stringify([issue.fields.description, $('Jira - Comentários').all().map(i => i.json.body)]);
const texto = norm(issue.fields.summary + ' ' + [...bruto.matchAll(/"(?:text|url|href)":"([^"]*)"/g)].map(m => m[1]).join(' '));
const stems = new Set(tokens(texto).map(stem));
const repos = [...texto.matchAll(/github\.com\/[\w.-]+\/([\w.-]+)\/pull/g)].map(m => norm(m[1]));

let tree = [];
try { tree = ($input.first().json.tree || []).map(t => t.path); } catch (e) {}
const notas = tree.filter(p => p.endsWith('.md') && !/(^|\/)[_.]/.test(p));

const pontua = p => {
  const partes = p.replace(/\.md$/, '').split('/');
  const base = partes.at(-1) === 'README' ? partes.at(-2) : partes.at(-1);
  let s = repos.includes(norm(base)) ? 10 : 0;
  for (const k of tokens(base)) if (!GEN.has(k) && stems.has(stem(k))) s += 3;
  for (const k of tokens(partes.slice(0, -1).join(' '))) if (!GEN.has(k) && stems.has(stem(k))) s += 1;
  return s;
};
const escolhidas = notas.map(p => ({ path: p, score: pontua(p) }))
  .filter(x => x.score >= 3).sort((a, b) => b.score - a.score).slice(0, 2);

// sempre devolve pelo menos 1 item para o fluxo continuar
return escolhidas.length ? escolhidas.map(x => ({ json: x })) : [{ json: { path: '', score: 0 } }];
```

### B5c. **KB - Lê notas**: HTTP Request
- GET `https://api.github.com/repos/movingpay/knowledge-base/contents/{{ $json.path.split('/').map(encodeURIComponent).join('/') }}`
- Authentication: **GitHub API**
- Header: `Accept` = `application/vnd.github.raw+json` (devolve o .md puro)
- Options → **Response** → Response Format: **Text** · Put Output in Field: `data`
- Settings → **On Error: Continue** · **Always Output Data**: on

### B5d. **DSMM - Índice**: HTTP Request (notas DSMM que já existem)
- GET `https://api.github.com/repos/movingpay/base-conhecimento-dsmm/contents/indice.json`
- Authentication: **GitHub API**
- Header: `Accept` = `application/vnd.github.raw+json`
- Options → **Response** → Response Format: **Text** · Put Output in Field: `data`
- Settings → **Execute Once**: on · **On Error: Continue** · **Always Output Data**: on (antes da primeira nota o arquivo pode não existir)

### B6. **Monta contexto**: Code (Run Once for All Items)
Junta tudo, **mascara dados sensíveis**, corta textos longos e escolhe até 3 notas DSMM parecidas. Troque `SEU-SITE`.

```js
const JIRA = 'https://SEU-SITE.atlassian.net';
const issue = $('Jira - Ticket').first().json;
const f = issue.fields;
const comments = $('Jira - Comentários').all().map(i => i.json).filter(c => c.body);
let prFiles = [], prUrl = '';
try { prFiles = $('GitHub - Arquivos do PR').all().map(i => i.json).filter(x => x.filename); } catch (e) {}
try { prUrl = $('GitHub - Busca PR').first().json.items?.[0]?.html_url || ''; } catch (e) {}

// Jira Cloud devolve descrição e comentários em ADF (JSON) → texto puro
// (mantém links, listas, `código` e menções; descarta imagens)
const adf = (n) => {
  if (!n) return '';
  if (typeof n === 'string') return n;
  if (Array.isArray(n)) return n.map(adf).join('');
  switch (n.type) {
    case 'text': {
      const link = (n.marks || []).find(m => m.type === 'link');
      const code = (n.marks || []).some(m => m.type === 'code');
      const t = code ? '`' + n.text + '`' : n.text;
      return link && link.attrs?.href !== n.text ? `${t} (${link.attrs.href})` : t;
    }
    case 'inlineCard': case 'blockCard': case 'embedCard': return n.attrs?.url || '';
    case 'mention': case 'emoji': case 'status': return n.attrs?.text || '';
    case 'hardBreak': return '\n';
    case 'media': case 'mediaSingle': case 'mediaGroup': case 'mediaInline': return '';
    case 'listItem': return '- ' + adf(n.content).trim() + '\n';
    case 'codeBlock': return '\n```\n' + adf(n.content) + '\n```\n';
    case 'paragraph': case 'heading': case 'blockquote': case 'panel': return adf(n.content) + '\n';
    default: return adf(n.content);
  }
};

// Mascarar dados sensíveis (primeira barreira; acrescente padrões próprios se precisar)
const mask = t => (t || '')
  .replace(/\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}\b/g, '[CNPJ]')
  .replace(/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g, '[CPF]')
  .replace(/\b(?:\d[ -]?){13,19}\b/g, '[CARTAO]')
  .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[EMAIL]')
  .replace(/\b(bearer|token|senha|password|secret|apikey|api_key)\b\s*[:=]?\s*\S+/gi, '$1 [REMOVIDO]');

const cut = (t, n) => t.length > n ? t.slice(0, n) + '\n…[truncado]' : t;

const coments = comments.slice(-10)
  .map(c => `### ${c.author?.displayName} (${(c.created || '').slice(0, 10)})\n${cut(mask(adf(c.body)), 2000)}`)
  .join('\n\n');

// Se a busca do PR não achou nada, usa o primeiro link de PR citado nos comentários
if (!prUrl) prUrl = (coments.match(/https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/\d+/) || [''])[0];
const diff = cut(mask(prFiles.map(p => `### ${p.filename}\n${p.patch || ''}`).join('\n')), 3000);

// Base de conhecimento: notas escolhidas (B5b/B5c) + nomes para [[links]] (só das pastas dessas notas)
const nomeNota = p => { const a = p.replace(/\.md$/, '').split('/'); return a.at(-1) === 'README' ? a.at(-2) : a.at(-1); };
let kb = '', nomesKB = [];
try {
  const paths = $('KB - Escolhe notas').all().map(i => i.json.path).filter(Boolean);
  kb = $('KB - Lê notas').all()
    .map((i, k) => paths[k] && typeof i.json.data === 'string'
      ? `### [[${nomeNota(paths[k])}]] (${paths[k]})\n${cut(i.json.data.replace(/^---[\s\S]*?---\s*/, ''), 2500)}` : '')
    .filter(Boolean).join('\n\n');
  const pastas = new Set(paths.map(p => p.split('/').slice(0, -1).join('/')));
  nomesKB = [...new Set(($('KB - Árvore').first().json.tree || []).map(t => t.path)
    .filter(p => p.endsWith('.md') && pastas.has(p.split('/').slice(0, -1).join('/')))
    .map(nomeNota))].slice(0, 15);
} catch (e) {}

// Notas DSMM parecidas (indice.json do repositório) — só título e resumo vão para a IA
const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const tokens = s => norm(s).split(/[^a-z0-9]+/).filter(t => t.length >= 4);
const STOP = new Set(['para','como','quando','erro','falha','problema','ticket','dsmm','geral','movingpay','sistema','nota','com','sem']);
const stemsTicket = new Set(tokens(f.summary + ' ' + adf(f.description) + ' ' + coments)
  .filter(t => !STOP.has(t)).map(t => t.slice(0, 7)));
let indice = [];
try { const d = $('DSMM - Índice').first().json; indice = Array.isArray(d) ? d : (d.data && typeof d.data === 'string' ? JSON.parse(d.data) : (Array.isArray(d.data) ? d.data : [])); } catch (e) {}
const candidatos = indice.map(n => {
  const ja = (n.tickets || []).includes(issue.key);
  const s = new Set(tokens(`${n.titulo} ${(n.tags || []).join(' ')} ${n.resumo}`).filter(t => !STOP.has(t)).map(t => t.slice(0, 7)));
  let score = 0; for (const t of s) if (stemsTicket.has(t)) score++;
  return { caminho: n.caminho, titulo: n.titulo, resumo: n.resumo, tickets: n.tickets || [], ja, score: ja ? 999 : score };
}).filter(n => n.score >= 3).sort((a, b) => b.score - a.score).slice(0, 3);
const txtCandidatos = candidatos.map(n =>
  `- caminho: ${n.caminho}${n.ja ? '  (JÁ CONTÉM ESTE TICKET)' : ''}\n  título: ${n.titulo}\n  tickets: ${n.tickets.join(', ')}\n  resumo: ${n.resumo}`).join('\n');

const contexto = `TICKET: ${issue.key} — ${mask(f.summary)}
TIPO JIRA: ${f.issuetype?.name}
COMPONENTES: ${(f.components || []).map(c => c.name).join(', ')}
LABELS: ${(f.labels || []).join(', ')}

DESCRIÇÃO:
${cut(mask(adf(f.description)), 3000)}

COMENTÁRIOS (mais recentes):
${coments || '(sem comentários)'}

ALTERAÇÕES NO PR:
${diff || '(PR não encontrado)'}

NOTAS DSMM PARECIDAS JÁ EXISTENTES (decida se é o mesmo problema):
${txtCandidatos || '(nenhuma)'}

NOTAS DA BASE DE CONHECIMENTO RELACIONADAS (use para explicar o contexto do sistema):
${kb || '(nenhuma nota relacionada encontrada)'}

NOTAS EXISTENTES PARA [[WIKILINK]]:
${nomesKB.join(', ') || '(lista indisponível)'}`;

return [{ json: {
  key: issue.key,
  url: `${JIRA}/browse/${issue.key}`,
  titulo_jira: mask(f.summary),
  tipo_jira: f.issuetype?.name || '',
  responsavel_email: f.assignee?.emailAddress || '',
  responsavel_nome: f.assignee?.displayName || '',
  resolvido_em: (f.resolutiondate || f.statuscategorychangedate || new Date().toISOString()).slice(0, 10),
  pr_url: prUrl,
  tem_comentarios: comments.length > 0,
  candidatos,
  ja_existe: candidatos.find(n => n.ja)?.caminho || '',
  caminhos_existentes: indice.map(n => n.caminho),
  contexto,
  feedback: ''
}}];
```

### B6b. **Tem comentários?**: IF
- Condição: `{{ $json.tem_comentarios }}` → Boolean → *is true* → segue para a **IA**.
- Saída **false**: encerra sem chamar a IA (ticket sem comentário quase nunca traz a solução). Economiza cota.

### B7. **IA**: Basic LLM Chain
- ⚠ **Source for Prompt (User Message): Define below.**
- ⚠ **O campo do prompt precisa estar em modo _Expression_** (botão *Fixed / Expression* acima do campo, ou o texto começando com `=`). Em modo *Fixed*, a IA recebe o texto literal `{{ $json.contexto }}` em vez do ticket e responde que "não foi fornecido contexto". Em modo Expression, a prévia logo abaixo do campo mostra o ticket de verdade.
- Sub-nó **Chat Model**: Anthropic Chat Model (ex.: Claude Sonnet), temperatura 0.2, **Maximum Number of Tokens: 4096** (a nota agora é mais longa).
- Ligue **Require Specific Output Format** e conecte um **Structured Output Parser** usando o exemplo de `n8n/prompts/output-schema.json`:

```json
{
  "documentar": true,
  "motivo": "",
  "acao": "nova",
  "nota_existente": "",
  "adendo": "",
  "sistema": "BackOffice",
  "titulo": "Exportação do relatório analítico estoura timeout de 60s no ALB",
  "tags": ["timeout", "relatorio", "performance"],
  "corpo": "# 🐛 Exportação do relatório analítico estoura timeout de 60s no ALB\n\n> [!summary] Resumo\n> ...\n\n## Contexto\n..."
}
```

- **System message** (o mesmo texto de `n8n/prompts/system.md`):
~~~
Você é um engenheiro de software sênior da MovingPay e escreve notas para a base de
conhecimento técnica da empresa (Obsidian). Sua tarefa: transformar um chamado DSMM resolvido
(bug ou melhoria) numa nota que ensine outro desenvolvedor, inclusive alguém que nunca mexeu
nesse sistema, a entender o problema, a correção e como agir se acontecer de novo.

ONDE ESTÁ CADA INFORMAÇÃO NO CONTEXTO
- DESCRIÇÃO: sintoma, como reproduzir, tela ou endpoint afetado.
- COMENTÁRIOS: causa e solução (o que mudou, PRs, números de antes/depois, validação). Leia
  TODOS; são a fonte principal da causa raiz e da solução.
- ALTERAÇÕES NO PR: diff do código, quando houver.
- NOTAS DA BASE DE CONHECIMENTO: documentação do sistema envolvido. Use para explicar o
  contexto (o que é o módulo, como funciona, quais serviços participam).
- NOTAS DSMM PARECIDAS JÁ EXISTENTES: notas de chamados anteriores (título e resumo).

NOVA NOTA OU ATUALIZAÇÃO
- Se uma das NOTAS DSMM PARECIDAS trata do MESMO problema (mesmo sintoma no mesmo ponto do
  sistema ou mesma causa raiz): "acao": "atualizar", "nota_existente": o caminho exato dela, e
  em "adendo" (3 a 8 linhas) o que esta ocorrência acrescenta: cenário, variação do sintoma,
  causa diferente, correção adicional, PR. Deixe "corpo" vazio.
- Se uma delas estiver marcada "(JÁ CONTÉM ESTE TICKET)", atualize essa nota.
- Senão: "acao": "nova" e escreva o "corpo" completo. Na dúvida, prefira "nova".

REGRAS
- Use apenas o que está no contexto. Não invente nomes, números, endpoints ou passos.
- Se a causa não estiver escrita de forma explícita, deduza-a da solução e diga que é inferida.
- Nunca peça informações ao leitor ("Por favor, forneça..."). Se uma seção não tiver base no
  contexto, escreva só "Não informado no ticket." nela.
- Nunca inclua nome de cliente, CPF/CNPJ, cartões, e-mails, tokens ou senhas.
- [[wikilinks]] só para nomes que aparecem em "NOTAS EXISTENTES PARA [[WIKILINK]]", escritos
  exatamente igual. Outros sistemas: texto normal ou `código`.
- Ignore imagens e anexos.

ESTILO (igual às notas da base: técnico, direto, de engenheiro para engenheiro)
- Markdown do Obsidian: tabelas para dados estruturados, `código` para nomes de arquivos,
  funções, tabelas e endpoints; callouts > [!summary], > [!warning], > [!tip], > [!important].
- Diagrama mermaid só quando ajudar a entender um fluxo (flowchart TD curto, rótulos entre aspas).

CAMPO "corpo": a nota completa em Markdown, nesta estrutura:

# 🐛 <título>        (🐛 para bug, ✨ para melhoria)

> [!summary] Resumo
> 2 a 3 frases: o que acontecia, por que acontecia e como foi resolvido.

## Contexto
O sistema e a funcionalidade envolvidos, para quem não conhece: tela, endpoint,
serviço/repositório, tabelas. Use as notas da base e linke com [[...]].

## Sintoma
O que o usuário via, mensagem ou código de erro, e como reproduzir (lista numerada).

## Causa raiz
Explicação técnica do porquê. Inclua trecho de código, query ou config em bloco de código
quando o contexto trouxer.

## Solução
O que mudou, agrupado por repositório/PR (com link). Números de antes/depois em tabela.

## Fluxo
(Opcional. Só com mermaid, se ajudar. Senão, omita a seção.)

## Como validar
Passos objetivos para confirmar a correção.

## Se acontecer de novo
> [!tip] Como reconhecer e diagnosticar
Sinais (erros, logs, métricas), o que verificar primeiro e prevenção ou débitos técnicos
que ficaram.

## Referências
- PRs (links) e notas relacionadas ([[...]]).

Não escreva a seção "Ocorrências": ela é gerada automaticamente.

OUTROS CAMPOS
- "titulo": nome do problema em si, como título de artigo (sintoma + onde acontece), sem nome
  de cliente e sem número de ticket. Ex.: "Exportação do relatório analítico estoura timeout
  de 60s no ALB".
- "sistema": exatamente um de [Registradora, CERC, B3, TAG, SLC, BS2, Manager, BackOffice, Console, IAM, Outro].
- "tags": 3 a 6 palavras-chave técnicas, minúsculas, sem espaço.
- "documentar": false só se o ticket não tiver nenhuma solução técnica (cancelado, duplicado,
  dúvida respondida). Explique em "motivo".
~~~
- **Prompt (user)**, em modo **Expression**:
```
Gere a nota de resolução do chamado abaixo.

{{ $json.contexto }}
{{ $json.feedback ? '\n\nAJUSTES PEDIDOS PELO RESPONSÁVEL (aplique na nova versão):\n' + $json.feedback : '' }}
```

### B8. **Documentar?**: IF
- Condição: `{{ $json.output.documentar }}` → Boolean → *is true*.
- Saída **false**: opcionalmente, um Jira → Issue Comment → Add com o texto `Sem nota de resolução: {{ $json.output.motivo }}`.

### B8b. **Ação?**: IF
- Condição: `{{ $json.output.acao }}` → String → *is equal to* → `atualizar`.
- **true** → **DSMM - Nota existente** → **Monta MD**. **false** → direto para o **Monta MD**.

### B8c. **DSMM - Nota existente**: HTTP Request
- GET `https://api.github.com/repos/movingpay/base-conhecimento-dsmm/contents/{{ $json.output.nota_existente.split('/').map(encodeURIComponent).join('/') }}`
- Authentication: **GitHub API** · Header `Accept` = `application/vnd.github.raw+json`
- Options → **Response** → Response Format: **Text** · Put Output in Field: `data`
- Settings → **On Error: Continue** (se falhar, o Monta MD cria uma nota nova)

### B9. **Monta MD**: Code (Run Once for All Items)
Cria a nota nova (arquivo com o nome do problema) **ou** acrescenta a ocorrência na nota existente: adiciona o ticket em `tickets`, atualiza `updated` e escreve o bloco `### DSMM-xxx` em **Ocorrências**. Se o mesmo ticket rodar de novo, o bloco dele é substituído, não duplicado. Os valores do cabeçalho vão entre aspas, então um `:` no texto não quebra o YAML.
```js
const c = $('Monta contexto').first().json;
const r = $('IA').first().json.output;
const SISTEMAS = ['Registradora','CERC','B3','TAG','SLC','BS2','Manager','BackOffice','Console','IAM','Outro'];
const sistema = SISTEMAS.find(s => s.toLowerCase() === String(r.sistema || '').toLowerCase()) || 'Outro';
const tipo = c.tipo_jira === 'Bug' ? 'bug' : 'melhoria';
const titulo = String(r.titulo || c.titulo_jira).replace(/\s+/g, ' ').trim();
const y = v => JSON.stringify(v ?? '');
const hoje = new Date().toISOString().slice(0, 10);
const slug = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60).replace(/-[^-]*$/, m => m.length < 3 ? '' : m);
const ocorrencia = (texto) => `### ${c.key} · ${c.resolvido_em} · ${c.responsavel_nome || 'sem responsável'}\n${texto.trim()}\n`;

// Texto da nota existente (só quando a IA decidiu atualizar)
let existente = '';
try { existente = String($('DSMM - Nota existente').first().json.data || ''); } catch (e) {}
const alvo = c.candidatos.find(n => n.caminho === r.nota_existente);
const atualizar = r.acao === 'atualizar' && alvo && existente.startsWith('---');

let md, caminho, acao;
if (atualizar) {
  acao = 'atualizar';
  caminho = alvo.caminho;
  md = existente
    .replace(/^tickets:.*$/m, l => { let t = []; try { t = JSON.parse(l.slice(8)); } catch (e) {}
      return `tickets: ${JSON.stringify([...new Set([...t, c.key])])}`; })
    .replace(/^updated:.*$/m, `updated: ${hoje}`);
  const bloco = ocorrencia(r.adendo || 'Mesma causa e solução da nota.');
  const re = new RegExp(`### ${c.key} · [\\s\\S]*?(?=\\n### |\\n## |$)`);
  if (re.test(md)) md = md.replace(re, bloco.trimEnd());
  else if (/\n## Ocorrências\s*\n/.test(md)) md = md.trimEnd() + '\n\n' + bloco;
  else md = md.trimEnd() + '\n\n## Ocorrências\n\n' + bloco;
} else {
  acao = 'nova';
  const tags = [...new Set(['dsmm', tipo, sistema.toLowerCase(), ...(r.tags || []).map(t => String(t).toLowerCase())])];
  caminho = c.ja_existe || `dsmm/${sistema.toLowerCase()}/${slug(titulo) || c.key.toLowerCase()}.md`;
  if (!c.ja_existe && c.caminhos_existentes.includes(caminho)) caminho = caminho.replace(/\.md$/, `-${c.key.toLowerCase()}.md`);
  const corpo = String(r.corpo || '').trim() || `# ${titulo}\n\nNão informado no ticket.`;
  md = `---
title: ${y(titulo)}
tags: ${JSON.stringify(tags)}
created: ${hoje}
updated: ${hoje}
tickets: ${JSON.stringify([c.key])}
sistema: ${y(sistema)}
tipo: ${tipo}
pr: ${y(c.pr_url)}
---

${corpo}

## Ocorrências

${ocorrencia(`Primeira ocorrência: deu origem a esta nota. [Ticket](${c.url})${c.pr_url ? ` · [PR](${c.pr_url})` : ''}`)}`;
}

const preview = acao === 'atualizar'
  ? `🔁 Atualiza a nota existente \`${caminho}\` com esta ocorrência:\n\n${r.adendo || ''}`
  : `🆕 Nota nova \`${caminho}\`\n\n${md.replace(/^---[\s\S]*?---\s*/, '')}`;

return [{ json: { ...c, ...r, acao, sistema, tipo, titulo: atualizar ? alvo.titulo : titulo, md, caminho, preview } }];
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
📚 *{{ $('Monta MD').first().json.key }}: {{ $('Monta MD').first().json.titulo }}*
{{ $('Monta MD').first().json.sistema }} · <{{ $('Monta MD').first().json.url }}|abrir ticket>

```{{ $('Monta MD').first().json.preview.slice(0, 2500) }}```
~~~
- Response Type: **Custom Form** → Define Form: **Using Fields Below** → **Add Form Element**:
  1. Field Name `Decisão` · Element Type **Dropdown List** · opções `Aprovar`, `Ajustar`, `Rejeitar` · Required Field: on
  2. Field Name `Observação` · Element Type **Textarea**. Se a sua versão do n8n não tiver essa opção, use **Text**, que funciona igual, só com a caixa menor. Required Field: off.
- ⚠ **Os campos não aparecem no card do Slack.** O Slack mostra só a mensagem e um botão. O dev clica no botão, e o formulário com Decisão e Observação abre no navegador, servido pelo n8n.
- Se preferir decidir direto no Slack, sem abrir o navegador, use Response Type **Approval** → Type of Approval: **Approve and Disapprove**. Assim o card mostra os botões Aprovar e Rejeitar, mas você perde o "Ajustar" (B16 deixa de existir e o Switch passa a ter só duas saídas).
- Options → **Limit Wait Time**: 48 horas · **Message Button Label**: `Revisar nota`

### B12. **Decisão**: Switch (Rules)
- Valor: `{{ $json.data['Decisão'] }}`. Confira o nome exato do campo na saída do B11 no primeiro teste.
- Regras: `Aprovar` → B13 · `Ajustar` → B16 · `Rejeitar` → B17
- Options → **Fallback Output: Extra Output** → B18 (sem resposta em 48h)

### B13. Salvar no GitHub
1. **GitHub - Existe?**: GitHub → File → Get
   - Owner: `movingpay` · Repository: `base-conhecimento-dsmm` · File Path: `{{ $('Monta MD').first().json.caminho }}`
   - Settings → **On Error: Continue (using error output)**
2. Saída de **sucesso** (o arquivo já existe) → **GitHub → File → Edit**. Saída de **erro** (o arquivo não existe) → **GitHub → File → Create**. Os dois com:
   - File Path: `{{ $('Monta MD').first().json.caminho }}`
   - File Content: `{{ $('Monta MD').first().json.md }}`
   - Commit Message: `docs(dsmm): {{ $('Monta MD').first().json.acao === 'atualizar' ? 'ocorrência' : 'nova nota' }} {{ $('Monta MD').first().json.key }} — {{ $('Monta MD').first().json.titulo }}`

### B14. Comentário no Jira: Jira Software → Issue Comment → Add
- Issue Key: `{{ $('Monta MD').first().json.key }}`
- Texto: `📚 Nota de resolução publicada: https://github.com/movingpay/base-conhecimento-dsmm/blob/main/{{ $('Monta MD').first().json.caminho }}`

### B15. Confirmação: Slack → Message → Send
- Para o usuário `{{ $('Slack - Usuário').first().json.user.id }}`: `✅ Nota {{ $('Monta MD').first().json.key }} publicada.`

### B16. **Ajuste**: Edit Fields (Set) → IF → volta para a IA
- Campos:
  - `contexto` = `{{ $('Monta contexto').first().json.contexto }}`
  - `feedback` = `{{ $('Slack - Aprovação').first().json.data['Observação'] }}`
  - `tentativa` = `{{ $runIndex + 1 }}`
- IF `tentativa <= 2` → liga de volta na entrada do nó **IA** (B7).
- Se passar de 2: Slack para o dev → "Ajuste direto no GitHub/Obsidian: {{ caminho }}".

### B17. Rejeitar: Jira → Issue Comment → Add (opcional)
- `Nota de resolução rejeitada pelo responsável.` e o fluxo encerra.

### B18. Sem resposta: Slack → Message → Send
- Para o tech lead ou o canal `#dsmm-notas`: `⏰ {{ $('Monta MD').first().json.key }} está sem revisão há 48h.`

---

## 3. Workflow A: "DSMM - Coletor"

### A1. Schedule Trigger
- A cada **10 minutos**. Para rodar só em horário comercial, use Cron: `*/10 8-19 * * 1-5`.

### A2. **Jira - Buscar resolvidos**: Jira Software → Issue → Get Many
- Return All: on · Options → **JQL**:
```
project = DSMM
AND issuetype in (Bug, História, Tarefa)
AND statusCategory = Done
AND statusCategoryChangedDate >= -7d
AND (labels is EMPTY OR labels not in (kb-processado))
```
- A JQL foi conferida no Jira da MovingPay em 16/11/2026. No projeto DSMM:
  - **Não existe o tipo "Melhoria".** Os tipos são Bug, História, Tarefa e Subtarefa. Melhoria entra como História.
  - **O campo Resolução nunca é preenchido** e o `resolved` fica vazio. Por isso a data usada é `statusCategoryChangedDate`, a data em que o ticket entrou em "Concluído" ou "Fechada".
  - Os status finais são **Concluído** e **Fechada**. Os dois têm a categoria Done, e o `statusCategory = Done` pega ambos.
- O `labels is EMPTY` é necessário porque `labels not in (...)` sozinho ignora os tickets sem nenhuma label.
- `-7d` impede que a primeira execução processe o histórico todo. Para gerar notas de tickets antigos, aumente esse prazo temporariamente (com `-30d` foram 30 tickets).

### A3. **Jira - Marca label**: HTTP Request
- PUT `https://SEU-SITE.atlassian.net/rest/api/3/issue/{{ $json.key }}`
- Authentication: Predefined → **Jira SW Cloud API**
- Body (JSON): `{"update":{"labels":[{"add":"kb-processado"}]}}`
- Use HTTP em vez do nó Jira "Update", porque o Update substitui todas as labels.

### A3b. **Um por vez**: Loop Over Items
Para não estourar o limite de requisições por minuto da API gratuita, os tickets são enviados um por vez, com 30 s entre eles.
- Batch Size: `1`
- Saída **loop** → A4 → A5 → volta para a entrada do **Um por vez**. A saída **done** fica sem nada.
- (Opcional) Antes do loop, um nó **Limit** com Max Items `5` limita quantos tickets entram por rodada de 10 minutos. Os outros ficam para a próxima rodada; para isso, mova o A3 (label) para depois do Limit.

### A4. Execute Workflow (Execute Sub-workflow)
- Source: **Database** → **DSMM - Gerar nota**
- Mode: **Run once for each item**
- Workflow Inputs → `key` = `{{ $json.key }}`. Se aparecer vazio, use `{{ $('Jira - Buscar resolvidos').item.json.key }}`.
- Options → **Wait For Sub-Workflow Completion: off**

### A5. **Pausa**: Wait
- Resume: **After Time Interval** · `30` seconds

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
| O workflow A não acha nenhum ticket | Tipo ou campo inexistente na JQL (ex.: "Melhoria", `resolved`, `resolution`) | Usar a JQL da seção 3 e testar na busca do Jira |
| `Slack - Usuário` retorna `ok: false` | O Jira não expôs o e-mail do responsável | Usar o canal como alternativa ou uma tabela Jira → Slack |
| O link de aprovação não abre | Dev fora da rede/VPN ou `WEBHOOK_URL` errado | Conferir a variável e o acesso à rede |
| Aviso de certificado no navegador | Certificado não confiável ou sem o IP no SAN | Reemitir com SAN e distribuir via GPO |
| Nó do GitHub: `Cannot read properties of undefined (reading 'endsWith')` | O campo **File Path** está vazio (`undefined`), geralmente por usar `$json.caminho` depois do Switch ou da saída de erro | Usar `{{ $('Monta MD').first().json.caminho }}` e conferir a prévia do campo |
| Nota cheia de "não fornecido" / "contexto ausente" | A IA recebeu o texto literal `{{ $json.contexto }}` ou nada | B7: prompt em modo **Expression** e *Source for Prompt* = **Define below**; a prévia do campo tem que mostrar o ticket |
| A nota não cita nada da base de conhecimento | Token sem acesso ao `knowledge-base` ou nenhuma nota combinou | Ver a saída do **KB - Escolhe notas** e do **KB - Lê notas** |
| `Error in user YAML: mapping values are not allowed` | `:` sem aspas no frontmatter | Usar o B9 atual (valores entre aspas) |
| GitHub retorna 404 | O token não tem acesso ao repositório | Ajustar o fine-grained token |
| O PR nunca é encontrado | A chave do ticket não está no título do PR ou na branch | Combinar a convenção com os devs (ou ignorar: o B4 é opcional) |
| Problema repetido virou nota nova | A nota antiga não estava no `indice.json` (a Action ainda não tinha rodado) ou o resumo dela não tem palavras em comum | Ver o campo `candidatos` no **Monta contexto**; dá para juntar as notas à mão e rodar a Action |
| Nota antiga sem o campo `tickets` não recebe o ticket novo | Nota criada antes da versão 4 (`ticket:` no singular) | Apagar e gerar de novo, ou trocar à mão para `tickets: ["DSMM-xxx"]` |
| Preciso gerar a nota de um ticket de novo | — | Tirar a label `kb-processado` do ticket; ele entra na próxima rodada |

---

## 7. Custo e manutenção
- **Uma chamada de IA por ticket**, com cerca de 4 a 6 mil tokens de entrada e 1 a 1,5 mil de saída. Ticket sem comentário não chama a IA. Cada "Ajustar" no Slack custa mais uma chamada.
- Limites usados para caber na cota: descrição 3.000 caracteres; últimos 10 comentários com 2.000 cada; diff 3.000; 2 notas da knowledge-base com 2.500 cada; até 15 nomes para `[[links]]`; até 3 notas DSMM parecidas (só título e resumo).
- Revisar de tempos em tempos: lista de sistemas (no prompt e nas pastas do repositório), validade dos tokens (Jira, GitHub) e o certificado do n8n.
- **Futuro (opcional):** se quiser a nota em tempo real, um **Cloudflare Tunnel** publicando só `/webhook/dsmm-resolvido` permite que o Jira Automation chame o n8n direto, substituindo o workflow A. O workflow B continua igual.
