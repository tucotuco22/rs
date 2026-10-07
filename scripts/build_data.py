#!/usr/bin/env python3
"""
Constrói os arquivos de dados do mapa do RS a partir dos dados abertos do TSE
e da lista de municípios do IBGE (via BrasilAPI).

Saídas:
  data/municipios.json  -> 497 municípios com prefeito e vice (2025-2028)
  data/estado.json      -> governador/vice (atual+eleito) e senadores (atuais+eleitos)
"""
import csv
import json
import os
import unicodedata
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "data")
os.makedirs(OUT, exist_ok=True)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def load_csv(path: str):
    with open(path, encoding="latin-1", newline="") as f:
        return list(csv.DictReader(f, delimiter=";", quotechar='"'))


def load_overrides():
    p = os.path.join(OUT, "overrides.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_softwares():
    p = os.path.join(OUT, "softwares.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_municipios():
    rows = load_csv(os.path.join(RAW, "consulta_cand_2024_RS.csv"))
    ibge = json.load(open(os.path.join(RAW, "municipios_ibge.json"), encoding="utf-8"))
    overrides = load_overrides()
    softwares = load_softwares()

    # índice eleitos por município (nome normalizado)
    eleitos = {}
    for r in rows:
        if r["DS_SIT_TOT_TURNO"] == "ELEITO" and r["DS_CARGO"] in ("PREFEITO", "VICE-PREFEITO"):
            key = norm(r["NM_UE"])
            eleitos.setdefault(key, {})[r["DS_CARGO"]] = r

    municipios = []
    for m in ibge:
        key = norm(m["nome"])
        rec = {
            "codigo_ibge": m["codigo_ibge"],
            "nome": m["nome"].title(),
        }
        pre = eleitos.get(key, {}).get("PREFEITO")
        vic = eleitos.get(key, {}).get("VICE-PREFEITO")
        rec["prefeito"] = candidato(pre) if pre else None
        rec["vice_prefeito"] = candidato(vic) if vic else None

        # aplica override manual (cassação / suplementar / renúncia / morte)
        ov = overrides.get(m["codigo_ibge"]) or overrides.get(key)
        if ov:
            rec["nota"] = ov.get("nota", "")
            rec["fontes"] = ov.get("fontes", [])
            if "prefeito" in ov:
                rec["prefeito"] = ov["prefeito"]
            if "vice_prefeito" in ov:
                rec["vice_prefeito"] = ov["vice_prefeito"]
            if "gastos" in ov:
                rec["gastos"] = ov["gastos"]

        # softwares/tecnologia do município
        if m["codigo_ibge"] in softwares:
            rec["software"] = softwares[m["codigo_ibge"]]

        municipios.append(rec)

    municipios.sort(key=lambda x: x["nome"])
    with open(os.path.join(OUT, "municipios.json"), "w", encoding="utf-8") as f:
        json.dump(municipios, f, ensure_ascii=False, indent=2)

    # validação
    sem_pref = [x["nome"] for x in municipios if not x["prefeito"]]
    sem_vice = [x["nome"] for x in municipios if not x["vice_prefeito"]]
    print(f"municipios: {len(municipios)}")
    print(f"sem prefeito: {len(sem_pref)} {sem_pref[:20]}")
    print(f"sem vice:     {len(sem_vice)} {sem_vice[:20]}")


def candidato(r: dict) -> dict:
    return {
        "nome": r["NM_CANDIDATO"].title(),
        "nome_urna": r["NM_URNA_CANDIDATO"].title(),
        "partido": r["SG_PARTIDO"],
        "partido_nome": r["NM_PARTIDO"],
        "coligacao": r["NM_COLIGACAO"],
        "mandato": "2025-2028",
    }


def build_estado():
    rows = load_csv(os.path.join(RAW, "consulta_cand_2026_RS.csv"))

    def eleito(cargo):
        for r in rows:
            if r["DS_CARGO"] == cargo and r["DS_SIT_TOT_TURNO"] == "ELEITO":
                return r
        return None

    gov = eleito("GOVERNADOR")
    vgov = eleito("VICE-GOVERNADOR")
    sena = [r for r in rows if r["DS_CARGO"] == "SENADOR" and r["DS_SIT_TOT_TURNO"] == "ELEITO"]
    sup = [r for r in rows if r["DS_CARGO"] in ("1º SUPLENTE", "2º SUPLENTE") and r["DS_SIT_TOT_TURNO"] == "ELEITO"]

    def senador(r, suplentes):
        return {
            "nome": r["NM_CANDIDATO"].title(),
            "nome_urna": r["NM_URNA_CANDIDATO"].title(),
            "partido": r["SG_PARTIDO"],
            "partido_nome": r["NM_PARTIDO"],
            "coligacao": r["NM_COLIGACAO"],
            "numero": r["NR_CANDIDATO"],
            "mandato": "2027-2035",
            "suplentes": suplentes,
        }

    eleitos_2026 = []
    for s in sena:
        sups = [
            {"nome": x["NM_CANDIDATO"].title(), "partido": x["SG_PARTIDO"], "ordem": x["DS_CARGO"]}
            for x in sup
            if x["NR_CANDIDATO"] == s["NR_CANDIDATO"]
        ]
        eleitos_2026.append(senador(s, sups))

    estado = {
        "uf": "RS",
        "estado": "Rio Grande do Sul",
        "atualizado_em": "2026-10-06",
        "governador": {
            "atual": {
                "nome": "Eduardo Leite",
                "partido": "PSD",
                "mandato": "2023-2026",
                "nota": "Mandato vigente até 31/12/2026.",
            },
            "eleito": {
                "nome": gov["NM_CANDIDATO"].title() if gov else "",
                "nome_urna": gov["NM_URNA_CANDIDATO"].title() if gov else "",
                "partido": gov["SG_PARTIDO"] if gov else "",
                "coligacao": gov["NM_COLIGACAO"] if gov else "",
                "mandato": "2027-2030",
                "nota": "Eleito em 1º turno em 04/10/2026; posse prevista em 06/01/2027.",
            },
        },
        "vice_governador": {
            "atual": {"nome": "Gabriel Souza", "partido": "MDB", "mandato": "2023-2026"},
            "eleito": {
                "nome": vgov["NM_CANDIDATO"].title() if vgov else "",
                "partido": vgov["SG_PARTIDO"] if vgov else "",
                "mandato": "2027-2030",
            },
        },
        "senadores": {
            "atuais": [
                {"nome": "Paulo Paim", "partido": "PT", "mandato": "2019-2027"},
                {"nome": "Luis Carlos Heinze", "partido": "PP", "mandato": "2019-2027"},
                {"nome": "Hamilton Mourão", "partido": "Republicanos", "mandato": "2023-2031"},
            ],
            "eleitos_2026": eleitos_2026,
        },
        "fontes": [
            "https://dadosabertos.tse.jus.br/dataset/candidatos-2026",
            "https://agenciabrasil.ebc.com.br/politica/noticia/2026-10/luciano-zucco-e-eleito-governador-do-rs",
            "https://www12.senado.leg.br/noticias/materias/2026/10/04/rio-grande-do-sul-elege-sanderson-e-marcel-van-hattem-para-o-senado",
        ],
    }
    with open(os.path.join(OUT, "estado.json"), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    print("estado.json escrito.")


if __name__ == "__main__":
    build_municipios()
    build_estado()
