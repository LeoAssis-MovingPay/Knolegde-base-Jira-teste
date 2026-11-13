#!/usr/bin/env python3
"""Gera o índice do README a partir do frontmatter das notas em dsmm/."""
import pathlib, re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
README = RAIZ / "README.md"
INI, FIM = "<!-- INDICE:INICIO -->", "<!-- INDICE:FIM -->"


def frontmatter(texto):
    m = re.match(r"^---\s*\n(.*?)\n---", texto, re.S)
    dados = {}
    if m:
        for linha in m.group(1).splitlines():
            if ":" in linha:
                k, v = linha.split(":", 1)
                dados[k.strip()] = v.split("#")[0].strip().strip('"')
    return dados


notas = []
for arq in sorted((RAIZ / "dsmm").rglob("*.md")):
    d = frontmatter(arq.read_text(encoding="utf-8"))
    d["caminho"] = arq.relative_to(RAIZ).as_posix()
    d.setdefault("sistema", arq.parent.name)
    notas.append(d)

if not notas:
    corpo = "_Nenhuma nota ainda._"
else:
    partes = [f"**Total:** {len(notas)} notas\n"]
    for sistema in sorted({n["sistema"] for n in notas}, key=str.lower):
        grupo = sorted((n for n in notas if n["sistema"] == sistema),
                       key=lambda n: n.get("resolvido_em", ""), reverse=True)
        partes.append(f"### {sistema} ({len(grupo)})\n")
        partes.append("| Ticket | Título | Tipo | Resolvido em |\n|---|---|---|---|")
        for n in grupo:
            partes.append(f"| [{n.get('ticket', '?')}]({n['caminho']}) | {n.get('titulo', '')} "
                          f"| {n.get('tipo', '')} | {n.get('resolvido_em', '')} |")
        partes.append("")
    corpo = "\n".join(partes).strip()

texto = README.read_text(encoding="utf-8")
novo = re.sub(re.escape(INI) + ".*?" + re.escape(FIM), f"{INI}\n{corpo}\n{FIM}", texto, flags=re.S)
README.write_text(novo, encoding="utf-8")
print(f"Índice atualizado: {len(notas)} notas")
