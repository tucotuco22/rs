# Mapa Político do Rio Grande do Sul

Mapa interativo com os **497 municípios do Rio Grande do Sul** e uma base de conhecimento estruturada sobre a gestão municipal e estadual: prefeitos, vice-prefeitos, governador, vice-governador e senadores — além de dados de gastos das prefeituras (começando por Santa Maria/RS).

Publicado como **site estático** (Leaflet + GeoJSON) no **GitHub Pages**.

## O que o mapa mostra

- **Executivo estadual**: governador e vice — atual (mandato até 2026) e eleito em 2026 (posse em 2027).
- **Senadores**: os 3 senadores atuais e os 2 eleitos em outubro de 2026.
- **497 municípios**: prefeito(a) e vice-prefeito(a) eleitos para o mandato 2025–2028 (partido, coligação), coloridos por partido.
- **Gastos da prefeitura**: dados de aluguel/locação de imóveis de **Santa Maria/RS** (estrutura pronta para expandir a outros municípios).
- **Softwares/tecnologia**: sistemas de gestão municipal, office e outros por município (começando por 6 municípios).
- **Clipagem**: linha do tempo de material sobre o governador eleito — notícias, comunicações oficiais, posts, vídeos, entrevistas e agenda.

## Estrutura do repositório

```
rs/
├── index.html                  # Página do mapa
├── css/style.css               # Estilos
├── js/app.js                   # Lógica do mapa e painéis
├── data/                       # Base de conhecimento (JSON/GeoJSON)
│   ├── estado.json             # Governador, vice e senadores (atual + eleito)
│   ├── municipios.json         # 497 municípios com prefeito e vice
│   ├── municipios.geojson      # Malha IBGE + dados mesclados (para o mapa)
│   ├── overrides.json          # Correções curadas (cassação, renúncia, gastos)
│   ├── softwares.json          # Softwares/tecnologia por município
│   └── raw/                    # Dados brutos baixados (não versionado)
├── scripts/                    # Pipeline de dados (regeneração)
│   ├── build_data.py           # TSE + IBGE → municipios.json e estado.json
│   └── build_geojson.py        # Mescla dados na malha geográfica
├── clipagem/                   # Arquivo de clipping (versionado)
│   └── clips.json              # Itens por pessoa (governador, etc.)
└── README.md
```

## Fontes de dados

| Dado | Fonte |
|------|-------|
| Prefeitos e vices eleitos (2024) | [Dados abertos do TSE — Candidatos 2024](https://dadosabertos.tse.jus.br/dataset/candidatos-2024) |
| Governador, vice e senadores (2026) | [Dados abertos do TSE — Candidatos 2026](https://dadosabertos.tse.jus.br/dataset/candidatos-2026) |
| Malha municipal (geometria) | [IBGE — Malhas territoriais](https://servicodados.ibge.gov.br/api/v3/malhas/) |
| Lista de municípios (códigos IBGE) | [BrasilAPI](https://brasilapi.com.br/api/ibge/municipios/v1/RS) |
| Gastos (aluguel) de Santa Maria | [Portal da Transparência de Santa Maria](https://www.santamaria.rs.gov.br/transparencia) |

## Regenerar os dados

```bash
# 1. Baixa os dados brutos (TSE + IBGE)
mkdir -p data/raw && cd data/raw
curl -O https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip
curl -O https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip
curl -o rs_municipios.geojson "https://servicodados.ibge.gov.br/api/v3/malhas/estados/RS?intrarregiao=municipio&formato=application/vnd.geo+json&qualidade=intermediaria"
curl -o municipios_ibge.json "https://brasilapi.com.br/api/ibge/municipios/v1/RS"
unzip -o consulta_cand_2024.zip "consulta_cand_2024_RS.csv"
unzip -o consulta_cand_2026.zip "consulta_cand_2026_RS.csv"
cd ../..

# 2. Gera os arquivos finais
python3 scripts/build_data.py
python3 scripts/build_geojson.py
```

> Para correções pontuais (ex.: cassação, eleição suplementar) e dados de gastos, edite `data/overrides.json` antes de rodar `build_data.py`. O arquivo aceita `prefeito`, `vice_prefeito`, `gastos`, `nota` e `fontes` por município (chave = código IBGE).

## Esquema de dados (base de conhecimento)

`data/municipios.json` — lista de 497 registros:

```jsonc
{
  "codigo_ibge": "4316907",
  "nome": "Santa Maria",
  "prefeito": {
    "nome": "Rodrigo Decimo",
    "nome_urna": "Rodrigo Decimo",
    "partido": "PSDB",
    "partido_nome": "Partido da Social Democracia Brasileira",
    "coligacao": "Todos por Santa Maria",
    "mandato": "2025-2028"
  },
  "vice_prefeito": { "...": "..." },
  "gastos": {                       // opcional — expandível por município
    "aluguel": {
      "por_ano": { "2025": "R$ …" },
      "maiores_locadores": [ { "credor": "…", "valor": "…" } ]
    },
    "fontes": ["url"]
  },
  "nota": "", "fontes": []
}
```

Para adicionar gastos de outro município, insira o objeto `gastos` no registro correspondente (ou crie um override) seguindo o mesmo esquema — o painel do site renderiza automaticamente.

### Softwares/tecnologia por município

`data/softwares.json` — chaveado por código IBGE, com 4 categorias:

```jsonc
{
  "4316907": {
    "gestao_municipal": [ { "nome": "Pronim", "fornecedor": "Pronim", "uso": "…", "fonte": "url", "nota": "…" } ],
    "office": [ { "nome": "Microsoft", "fornecedor": "Microsoft", "fonte": "url" } ],
    "video_design": [],
    "outros": [ { "nome": "e-SIC / Ouvidoria", "uso": "…", "fonte": "url" } ]
  }
}
```

Adicione entradas por código IBGE e rode `python3 scripts/build_data.py` + `build_geojson.py`; o painel do município mostra a seção **Software e tecnologia**.

Municípios já preenchidos:

| Município | Sistema de gestão (ERP) | Outros |
|---|---|---|
| Santa Maria | Pronim (contabilidade/RH/transparência) | Site STI, e-SIC/Ouvidoria |
| Porto Alegre | Sigef-Poa (Minsait/Indra) | Procempa, DOPA, Microsoft |
| Caxias do Sul | GRP Thema (Grupo Thema/Pólis) | Microsoft |
| Pelotas | Coinpel (desenvolvimento próprio) + Proges | Projus, Ouvidoria/SIC |
| Canoas | Ábaco (transparência/NFS-e) | SEI, CanoasTec, site Ondaweb |
| Cachoeirinha | IPM Sistemas (Atende.Net) | eComunica |

## Clipagem

A clipagem é um arquivo de material sobre políticos, versionado no git (cada item adicionado vira um commit). Fica em `clipagem/clips.json`, com uma entrada por pessoa:

```jsonc
{
  "atualizado_em": "2026-10-06",
  "pessoas": [
    {
      "id": "zucco",
      "nome_completo": "Luciano Lorenzini Zucco",
      "cargo": "Governador eleito do Rio Grande do Sul (2027–2030)",
      "partido": "PL",
      "resumo": "…",
      "itens": [
        {
          "id": "2026-10-04-agenciabrasil",
          "data": "2026-10-04",                 // data de publicação
          "tipo": "noticia",                    // noticia | comunicado | post | video | entrevista | agenda | documento
          "titulo": "…",
          "fonte": "Agência Brasil",
          "url": "https://…",
          "resumo": "…",
          "tags": ["eleição", "resultado"]
        }
      ]
    }
  ]
}
```

Para adicionar material, use o helper (recomendado) ou edite o JSON à mão:

```bash
python3 scripts/add_clip.py \
  --pessoa zucco \
  --data 2026-10-06 \
  --tipo noticia \
  --titulo "Título da notícia" \
  --fonte "Agência Brasil" \
  --url "https://..." \
  --resumo "Resumo curto" \
  --tags "eleição,transição"
```

O script cria/atualiza a pessoa, ordena os itens por data e imprime o comando de commit sugerido. Alternativamente, edite `clipagem/clips.json` e acrescente um objeto no array `itens` da pessoa (ou crie uma nova pessoa em `pessoas`). Em seguida:

```bash
git add clipagem/clips.json && git commit -m "clipagem: <título>" && git push
```

O site exibe a clipagem na aba **Clipagem**, com filtro por tipo e linha do tempo ordenada por data. Fontes úteis para acompanhar: [Agência de Notícias do RS](https://estado.rs.gov.br/ultimas-noticias), [Agenda do Governador](https://estado.rs.gov.br/agenda-do-governador) e a imprensa.

## Fact-checking do plano de governo

O repositório guarda o plano de governo do governador eleito e uma estrutura de acompanhamento de promessas:

- `clipagem/documentos/plano-de-governo-zucco.pdf` — plano original (107 págs.).
- `clipagem/documentos/plano-de-governo-zucco.resumo.md` — resumo (6 eixos + 14 Projetos Prioritários).
- `clipagem/documentos/fact-checking-2027.md` — checklist com 71 indicadores de resultado.
- `clipagem/documentos/fact-checking-status.md` / `.json` — relatório de status gerado.

Fluxo:

1. Marque itens no checklist (`[x]` + `status` + evidência) e commite.
2. Regere o relatório de status:
   ```bash
   python3 scripts/fact_check_status.py
   ```
   Ele calcula percentual de cumprimento por **eixo** e por **projeto** e atualiza `fact-checking-status.md`/`.json`.

## Clipping dos diários oficiais (Querido Diário)

Integração com a API pública do [Querido Diário](https://queridodiario.ok.org.br/) (a mesma usada pelo [Ro-DOU](https://gestaogovbr.github.io/Ro-dou/)) para fazer clipping dos **diários oficiais municipais** por palavra-chave.

```bash
python3 scripts/clip_diario.py [--dias N]
```

- Configuração em `data/diario_config.json` (palavras-chave, municípios e janela em dias).
- Gera `clipagem/diarios/diarios.json` (estruturado) e `diarios.md` (relatório).
- Cobertura no RS é parcial: busca por texto (nível 3) em **Porto Alegre** e **Caxias do Sul**; **Canoas, Pelotas e Cachoeirinha** têm só lista (nível 1); **Santa Maria não está coberta**.

## Executar localmente

```bash
python3 -m http.server 8000
# abra http://localhost:8000
```

## Publicação

O site é estático e fica na raiz do repositório. No GitHub, ative **Settings → Pages → Source: Deploy from a branch → `main` / (root)**. Os arquivos `index.html`, `data/`, `css/` e `js/` são servidos diretamente.

## Aviso de atualidade

Dados políticos refletem a situação em **06/10/2026** (dois dias após o 1º turno das eleições de 2026). Municípios com cassação/eleição suplementar (ex.: Cachoeirinha, Arroio do Sal) são marcados com nota específica. Vereadores e deputados (federais/estaduais) ainda não estão incluídos nesta versão.
