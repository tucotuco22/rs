#!/usr/bin/env python3
"""
Clipping dos diários oficiais municipais via API Querido Diário.

Lê data/diario_config.json (palavras-chave + municípios) e gera:
  clipagem/diarios/diarios.json  -> resultados estruturados
  clipagem/diarios/diarios.md    -> relatório legível

Uso:
  python3 scripts/clip_diario.py [--dias N]

Obs.: a busca por texto (querystring) só funciona em municípios com nível 3
de cobertura no Querido Diário. A API tem limite de ~60 req/min.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASES = [
    "https://api.queridodiario.org.br/gazettes",
    "https://api.queridodiario.ok.org.br/gazettes",
]
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(BASE, "data", "diario_config.json")
OUT_DIR = os.path.join(BASE, "clipagem", "diarios")
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_json(url, retries=2):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mapa-rs/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(2 * (i + 1))
    raise last


def search(territory_id, querystring, since, until, size=50):
    params = {
        "territory_ids": territory_id,
        "querystring": querystring,
        "published_since": since,
        "published_until": until,
        "sort_by": "descending_date",
        "excerpt_size": 500,
        "number_of_excerpts": 2,
        "size": size,
    }
    qs = urllib.parse.urlencode(params)
    last = None
    for base in BASES:
        try:
            return fetch_json(base + "?" + qs)
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def truncate(s, n=300):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "…"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=None, help="janela retroativa em dias")
    args = ap.parse_args()

    cfg = json.load(open(CONFIG, encoding="utf-8"))
    palavras = cfg["palavras_chave"]
    municipios = cfg["municipios"]
    dias = args.dias or cfg.get("dias_retroativos", 30)

    hoje = datetime.date.today()
    since = (hoje - datetime.timedelta(days=dias)).isoformat()
    until = hoje.isoformat()

    clips = {}
    falhas = 0
    for m in municipios:
        for kw in palavras:
            try:
                data = search(m["territory_id"], kw, since, until)
            except Exception as e:  # noqa: BLE001
                falhas += 1
                print(f"  ! {m['nome']} / '{kw}': erro ({e})", file=sys.stderr)
                continue
            n = 0
            for g in data.get("gazettes", []):
                # filtro defensivo: a API pode devolver outros territórios
                if g.get("territory_id") != m["territory_id"]:
                    continue
                n += 1
                url = g.get("url") or g.get("txt_url")
                if url in clips:
                    clips[url]["palavras"].add(kw)
                    continue
                clips[url] = {
                    "municipio": m["nome"],
                    "territory_id": m["territory_id"],
                    "data": g.get("date"),
                    "edicao": g.get("edition"),
                    "extra": bool(g.get("is_extra_edition")),
                    "url": g.get("url"),
                    "txt_url": g.get("txt_url"),
                    "trechos": g.get("excerpts") or [],
                    "palavras": {kw},
                }
            print(f"  {m['nome']} / '{kw}': {n} diário(s)")
            time.sleep(0.5)  # cortesia com o limite de 60 req/min

    lista = sorted(clips.values(), key=lambda c: c.get("data", ""), reverse=True)

    out_json = {
        "gerado_em": hoje.isoformat(),
        "fonte": "Querido Diário (api.queridodiario.org.br)",
        "parametros": {"dias_retroativos": dias, "palavras_chave": palavras},
        "falhas": falhas,
        "total": len(lista),
        "clips": [
            {**c, "palavras": sorted(c["palavras"]), "trecho": truncate((c["trechos"] or [""])[0])}
            for c in lista
        ],
    }
    with open(os.path.join(OUT_DIR, "diarios.json"), "w", encoding="utf-8") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)
        f.write("\n")

    md = []
    md.append("# Clipping dos diários oficiais (Querido Diário)")
    md.append("")
    md.append(f"Gerado em **{hoje.isoformat()}** por `scripts/clip_diario.py`.")
    md.append(f"Janela: últimos **{dias} dias** · **{len(lista)}** diário(s) com correspondência.")
    md.append("")
    if lista:
        md.append("| Município | Data | Edição | Palavras | Trecho |")
        md.append("|---|---|---|---|---|")
        for c in lista:
            t = truncate((c["trechos"] or [""])[0], 160)
            link = f"[ver]({c['url']})" if c["url"] else "—"
            md.append(f"| {c['municipio']} | {c['data']} | {c['edicao'] or '—'} | {', '.join(sorted(c['palavras']))} | {t} {link} |")
    else:
        md.append("_Nenhuma correspondência no período._")
    md.append("")
    with open(os.path.join(OUT_DIR, "diarios.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\nTotal: {len(lista)} diário(s) em {len(municipios)} município(s) / {len(palavras)} palavra(s)-chave · {falhas} falha(s).")
    print(f"Gerados: clipagem/diarios/diarios.json e clipagem/diarios/diarios.md")


if __name__ == "__main__":
    main()
