#!/usr/bin/env python3
"""Mescla municipios.json (base de conhecimento) no GeoJSON do IBGE para o mapa."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "data")

municipios = {m["codigo_ibge"]: m for m in json.load(open(os.path.join(OUT, "municipios.json"), encoding="utf-8"))}

geo = json.load(open(os.path.join(RAW, "rs_municipios.geojson"), encoding="utf-8"))
for feat in geo["features"]:
    code = feat["properties"].get("codarea")
    rec = municipios.get(code, {})
    feat["properties"] = {
        "codigo_ibge": code,
        "nome": rec.get("nome"),
        "prefeito": rec.get("prefeito"),
        "vice_prefeito": rec.get("vice_prefeito"),
        "gastos": rec.get("gastos"),
        "software": rec.get("software"),
        "nota": rec.get("nota"),
        "fontes": rec.get("fontes"),
    }

with open(os.path.join(OUT, "municipios.geojson"), "w", encoding="utf-8") as f:
    json.dump(geo, f, ensure_ascii=False)

print(f"municipios.geojson: {len(geo['features'])} features, {os.path.getsize(os.path.join(OUT,'municipios.geojson'))} bytes")
