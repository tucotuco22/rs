#!/usr/bin/env python3
"""
Adiciona um item de clipagem em clipagem/clips.json.

Uso:
  python3 scripts/add_clip.py \
      --pessoa zucco \
      --data 2026-10-06 \
      --tipo noticia \
      --titulo "Título da notícia" \
      --fonte "Agência Brasil" \
      --url "https://..." \
      --resumo "Resumo curto" \
      --tags "eleição,transição"

Tipos aceitos: noticia | comunicado | post | video | entrevista | agenda | documento
Se a pessoa não existir, crie-a com --nome-completo, --cargo e --partido.
"""
import argparse
import datetime
import json
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(BASE, "clipagem", "clips.json")

TIPOS = {"noticia", "comunicado", "post", "video", "entrevista", "agenda", "documento"}


def slug(s):
    s = unicodedata.normalize("NFD", s or "")
    s = s.encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")
    return s


def main():
    ap = argparse.ArgumentParser(description="Adiciona item de clipagem")
    ap.add_argument("--pessoa", required=True, help="id da pessoa (ex.: zucco)")
    ap.add_argument("--data", required=True, help="data de publicação (AAAA-MM-DD)")
    ap.add_argument("--tipo", required=True, choices=sorted(TIPOS), help="tipo do item")
    ap.add_argument("--titulo", required=True, help="título do item")
    ap.add_argument("--url", required=True, help="URL da fonte")
    ap.add_argument("--fonte", default="", help="veículo/origem (ex.: Agência Brasil)")
    ap.add_argument("--resumo", default="", help="resumo/trecho (opcional)")
    ap.add_argument("--tags", default="", help="tags separadas por vírgula (opcional)")
    ap.add_argument("--nome-completo", default="", help="nome completo (só ao criar pessoa)")
    ap.add_argument("--cargo", default="", help="cargo (só ao criar pessoa)")
    ap.add_argument("--partido", default="", help="partido (só ao criar pessoa)")
    args = ap.parse_args()

    if not os.path.exists(CLIPS):
        print(f"erro: {CLIPS} não encontrado.", file=sys.stderr)
        sys.exit(1)

    with open(CLIPS, encoding="utf-8") as f:
        data = json.load(f)

    # localiza ou cria a pessoa
    pessoa = next((p for p in data.get("pessoas", []) if p.get("id") == args.pessoa), None)
    criada = False
    if pessoa is None:
        if not args.nome_completo:
            print(f"erro: pessoa '{args.pessoa}' não existe; informe --nome-completo.", file=sys.stderr)
            sys.exit(1)
        pessoa = {
            "id": args.pessoa,
            "nome": args.nome_completo.split()[0] if args.nome_completo else args.pessoa,
            "nome_completo": args.nome_completo,
            "cargo": args.cargo,
            "partido": args.partido,
            "resumo": "",
            "itens": [],
        }
        data.setdefault("pessoas", []).append(pessoa)
        criada = True

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    item_id = f"{args.data}-{args.tipo}-{slug(args.titulo)[:60]}"
    item = {
        "id": item_id,
        "data": args.data,
        "tipo": args.tipo,
        "titulo": args.titulo,
        "fonte": args.fonte,
        "url": args.url,
        "resumo": args.resumo,
        "tags": tags,
    }

    # evita duplicar id
    if any(i.get("id") == item_id for i in pessoa["itens"]):
        print(f"aviso: já existe item com id '{item_id}'; nada foi alterado.", file=sys.stderr)
        sys.exit(1)

    pessoa["itens"].append(item)
    pessoa["itens"].sort(key=lambda i: str(i.get("data", "")), reverse=True)
    data["atualizado_em"] = datetime.date.today().isoformat()

    with open(CLIPS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    acao = "criada" if criada else "atualizada"
    total = len(pessoa["itens"])
    print(f"pessoa '{args.pessoa}' {acao} · item '{item_id}' adicionado ({total} itens).")
    print()
    print("Commit sugerido:")
    print(f'  git add clipagem/clips.json && git commit -m "clipagem({args.pessoa}): {args.titulo[:60]}" && git push')


if __name__ == "__main__":
    main()
