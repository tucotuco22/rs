#!/usr/bin/env python3
"""
Gera o relatório de status do fact-checking do Plano de Governo Zucco.

Lê clipagem/documentos/fact-checking-2027.md (checklist) e produz:
  - clipagem/documentos/fact-checking-status.md   (relatório legível)
  - clipagem/documentos/fact-checking-status.json (dados estruturados)

Uso: python3 scripts/fact_check_status.py
"""
import datetime
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(BASE, "clipagem", "documentos")
CHECKLIST = os.path.join(DOCS, "fact-checking-2027.md")
OUT_MD = os.path.join(DOCS, "fact-checking-status.md")
OUT_JSON = os.path.join(DOCS, "fact-checking-status.json")

# Mapeamento editorial de cada projeto prioritário ao seu eixo principal.
PROJETO_EIXO = {
    1: "5. Um Estado que Funciona",
    2: "1. Um Estado que Protege",
    3: "1. Um Estado que Protege",
    4: "4. Um Estado que Conecta",
    5: "3. Um Estado que Cresce",
    6: "3. Um Estado que Cresce",
    7: "2. Um Estado que Cuida",
    8: "3. Um Estado que Cresce",
    9: "4. Um Estado que Conecta",
    10: "4. Um Estado que Conecta",
    11: "4. Um Estado que Conecta",
    12: "6. Um Estado que Lidera",
    13: "2. Um Estado que Cuida",
    14: "5. Um Estado que Funciona",
}

STATUS_VALIDOS = {"a verificar", "em andamento", "cumprido", "parcial", "não cumprido"}


def parse():
    projetos = []
    atual = None
    with open(CHECKLIST, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^##\s+(\d+)\.\s+(.+?)\s*$", line)
            if m:
                atual = {"numero": int(m.group(1)), "titulo": m.group(2).strip(), "itens": []}
                projetos.append(atual)
                continue
            if atual and re.match(r"^-\s+\[([ xX])\]\s+", line):
                marcado = line.strip()[3] in ("x", "X")
                s = re.search(r"_status:\s*([^_]+)_", line)
                status = (s.group(1).strip() if s else "a verificar")
                if status not in STATUS_VALIDOS:
                    status = "a verificar"
                atual["itens"].append({"marcado": marcado, "status": status})
    return projetos


def stats(itens):
    total = len(itens)
    cumprido = sum(1 for i in itens if i["status"] == "cumprido")
    andamento = sum(1 for i in itens if i["status"] in ("em andamento", "parcial"))
    nao_cumprido = sum(1 for i in itens if i["status"] == "não cumprido")
    a_verificar = sum(1 for i in itens if i["status"] == "a verificar")
    pct = lambda n: (n / total * 100) if total else 0.0
    return {
        "total": total,
        "cumprido": cumprido,
        "em_andamento": andamento,
        "nao_cumprido": nao_cumprido,
        "a_verificar": a_verificar,
        "pct_concluido": pct(cumprido),
    }


def main():
    projetos = parse()
    hoje = datetime.date.today().isoformat()

    por_projeto = []
    for p in projetos:
        s = stats(p["itens"])
        por_projeto.append({"numero": p["numero"], "titulo": p["titulo"], **s})

    # agrega por eixo
    eixos = {}
    for p in por_projeto:
        eixo = PROJETO_EIXO.get(p["numero"], "? Eixo")
        eixos.setdefault(eixo, {"total": 0, "cumprido": 0, "em_andamento": 0, "nao_cumprido": 0, "a_verificar": 0})
        e = eixos[eixo]
        e["total"] += p["total"]
        e["cumprido"] += p["cumprido"]
        e["em_andamento"] += p["em_andamento"]
        e["nao_cumprido"] += p["nao_cumprido"]
        e["a_verificar"] += p["a_verificar"]

    total = sum(p["total"] for p in por_projeto)
    cumprido = sum(p["cumprido"] for p in por_projeto)
    andamento = sum(p["em_andamento"] for p in por_projeto)
    nao_cumprido = sum(p["nao_cumprido"] for p in por_projeto)
    a_verificar = sum(p["a_verificar"] for p in por_projeto)
    pct = lambda n: (n / total * 100) if total else 0.0

    # JSON
    data = {
        "gerado_em": hoje,
        "resumo": {
            "total": total,
            "cumprido": cumprido,
            "em_andamento": andamento,
            "nao_cumprido": nao_cumprido,
            "a_verificar": a_verificar,
            "pct_concluido": round(pct(cumprido), 1),
        },
        "por_eixo": [
            {
                "eixo": k,
                "total": v["total"],
                "cumprido": v["cumprido"],
                "em_andamento": v["em_andamento"],
                "nao_cumprido": v["nao_cumprido"],
                "a_verificar": v["a_verificar"],
                "pct_concluido": round(pct(v["cumprido"]), 1),
            }
            for k, v in sorted(eixos.items())
        ],
        "por_projeto": [
            {**p, "pct_concluido": round(pct(p["cumprido"]), 1)} for p in por_projeto
        ],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Markdown
    def linha(nome, s):
        p = s.get("pct_concluido", 0)
        return f"| {nome} | {s['total']} | {s['cumprido']} | {s['em_andamento']} | {s['nao_cumprido']} | {s['a_verificar']} | {p:.1f}% |"

    md = []
    md.append("# Relatório de status — Fact-checking do Plano de Governo Zucco (2027–2030)")
    md.append("")
    md.append(f"Gerado automaticamente em **{hoje}** por `scripts/fact_check_status.py`.")
    md.append("")
    md.append("## Resumo geral")
    md.append("")
    md.append(f"- Total de indicadores: **{total}**")
    md.append(f"- Cumpridos: **{cumprido}** ({pct(cumprido):.1f}%)")
    md.append(f"- Em andamento/parcial: **{andamento}** ({pct(andamento):.1f}%)")
    md.append(f"- Não cumpridos: **{nao_cumprido}** ({pct(nao_cumprido):.1f}%)")
    md.append(f"- A verificar: **{a_verificar}** ({pct(a_verificar):.1f}%)")
    md.append("")
    md.append("## Por eixo")
    md.append("")
    md.append("| Eixo | Total | Cumprido | Em andamento | Não cumprido | A verificar | % concluído |")
    md.append("|---|---|---|---|---|---|---|")
    for k, v in sorted(eixos.items()):
        v["pct_concluido"] = round(pct(v["cumprido"]), 1)
        md.append(linha(k, v))
    md.append("")
    md.append("## Por projeto prioritário")
    md.append("")
    md.append("| Projeto | Total | Cumprido | Em andamento | Não cumprido | A verificar | % concluído |")
    md.append("|---|---|---|---|---|---|---|")
    for p in por_projeto:
        md.append(linha(f"{p['numero']}. {p['titulo']}", p))
    md.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # stdout
    print(f"Total: {total} | cumprido: {cumprido} | em andamento: {andamento} | não cumprido: {nao_cumprido} | a verificar: {a_verificar}")
    print(f"Gerados: {os.path.relpath(OUT_MD, BASE)} e {os.path.relpath(OUT_JSON, BASE)}")


if __name__ == "__main__":
    main()
