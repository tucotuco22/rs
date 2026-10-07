#!/usr/bin/env python3
"""
Adiciona um item (link + título) a um município em data/links.json.

Uso:
  python3 scripts/add_link.py \
      --municipio "Santa Maria" \
      --titulo "Título do item" \
      --url "https://..." \
      [--fonte "Portal"] [--tipo "noticia"] [--data 2026-10-07]

O município pode ser o nome ou o código IBGE de 7 dígitos.
"""
import argparse
import datetime
import json
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS = os.path.join(BASE, "data", "links.json")
MUNICIPIOS = os.path.join(BASE, "data", "municipios.json")


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def carregar_municipios():
    with open(MUNICIPIOS, encoding="utf-8") as f:
        return json.load(f)


def resolve_codigo(municipio, lista):
    if municipio.isdigit() and len(municipio) == 7:
        return municipio
    alvo = norm(municipio)
    for m in lista:
        if norm(m["nome"]) == alvo:
            return m["codigo_ibge"]
    for m in lista:
        if alvo in norm(m["nome"]):
            return m["codigo_ibge"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--municipio", required=True, help="nome ou código IBGE")
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--fonte", default="")
    ap.add_argument("--tipo", default="noticia", help="noticia | documento | licitacao | contrato | outro")
    ap.add_argument("--data", default=None, help="AAAA-MM-DD (padrão: hoje)")
    args = ap.parse_args()

    lista = carregar_municipios()
    cod = resolve_codigo(args.municipio, lista)
    if not cod:
        print(f"erro: município '{args.municipio}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    data = {}
    if os.path.exists(LINKS):
        with open(LINKS, encoding="utf-8") as f:
            data = json.load(f)

    item = {
        "titulo": args.titulo,
        "url": args.url,
        "fonte": args.fonte,
        "tipo": args.tipo,
        "data": args.data or datetime.date.today().isoformat(),
    }
    data.setdefault(cod, []).insert(0, item)

    with open(LINKS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    nome = next((m["nome"] for m in lista if m["codigo_ibge"] == cod), cod)
    print(f"item adicionado a {nome} ({cod}). total neste município: {len(data[cod])}")
    print()
    print("commit sugerido:")
    print(f'  git add data/links.json && git commit -m "link: {nome} — {args.titulo[:60]}" && git push')


if __name__ == "__main__":
    main()
