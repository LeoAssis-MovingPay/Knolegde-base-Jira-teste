#!/usr/bin/env python3
"""Gera o índice (tabela no README.md + indice.json) a partir do frontmatter das notas em dsmm/.

O indice.json é lido pelo n8n para achar notas parecidas antes de chamar a IA.
"""
import json
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
README = RAIZ / "README.md"
INDICE = RAIZ / "indice.json"
INI, FIM = "<!-- INDICE:INICIO -->", "<!-- INDICE:FIM -->"


def valor(v):
    v = v.split(" #")[0].strip()
    if v[:1] in '["':
        try:
            return json.loads(v)
        except Exception:
            pass
    return v.strip('"')


def le_nota(arq):
    texto = arq.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", texto, re.S)
    dados, corpo = {}, texto
    if m:
        corpo = m.group(2)
        for linha in m.group(1).splitlines():
            if ":" in linha and not linha.startswith((" ", "\t")):
                k, v = linha.split(":", 1)
                dados[k.strip()] = valor(v)
    r = re.search(r"> \[!summary\][^\n]*\n((?:>.*\n?)+)", corpo)
    resumo = " ".join(l.lstrip(">").strip() for l in r.group(1).splitlines()).strip() if r else ""
    tickets = dados.get("tickets") or ([dados["ticket"]] if dados.get("ticket") else [])
    if isinstance(tickets, str):
        tickets = [tickets]
    tags = dados.get("tags") or []
    return {
        "caminho": arq.relative_to(RAIZ).as_posix(),
        "titulo": dados.get("title") or dados.get("titulo") or arq.stem,
        "sistema": dados.get("sistema") or arq.parent.name,
        "tipo": dados.get("tipo", ""),
        "tags": tags if isinstance(tags, list) else [tags],
        "tickets": tickets,
        "atualizado": dados.get("updated") or dados.get("resolvido_em", ""),
        "resumo": resumo[:400],
    }


notas = [le_nota(a) for a in sorted((RAIZ / "dsmm").rglob("*.md"))]
INDICE.write_text(json.dumps(notas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

if not notas:
    corpo = "_Nenhuma nota ainda._"
else:
    partes = [f"**Total:** {len(notas)} notas\n"]
    for sistema in sorted({n["sistema"] for n in notas}, key=str.lower):
        grupo = sorted((n for n in notas if n["sistema"] == sistema),
                       key=lambda n: str(n["atualizado"]), reverse=True)
        partes.append(f"### {sistema} ({len(grupo)})\n")
        partes.append("| Nota | Tickets | Tipo | Atualizada em |\n|---|---|---|---|")
        for n in grupo:
            partes.append(f"| [{n['titulo']}]({n['caminho']}) | {', '.join(n['tickets'])} "
                          f"| {n['tipo']} | {n['atualizado']} |")
        partes.append("")
    corpo = "\n".join(partes).strip()

texto = README.read_text(encoding="utf-8")
novo = re.sub(re.escape(INI) + ".*?" + re.escape(FIM), f"{INI}\n{corpo}\n{FIM}", texto, flags=re.S)
README.write_text(novo, encoding="utf-8")
print(f"Índice atualizado: {len(notas)} notas")
