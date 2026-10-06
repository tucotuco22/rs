/* Mapa Político do Rio Grande do Sul — app.js */
(function () {
  "use strict";

  var estado = null;
  var geoLayer = null;
  var features = [];
  var nameIndex = {}; // nome normalizado -> feature
  var selected = null;
  var map = null;
  var clips = null;
  var clipFilter = "todos";

  var PARTY_COLORS = {
    "PT": "#e0342e", "PL": "#2c5fae", "MDB": "#3f7d3a", "PP": "#2a4f9e",
    "PSDB": "#1f6fb2", "PDT": "#d2232a", "PSB": "#e0212c", "PSD": "#e8a200",
    "REPUBLICANOS": "#1a7a46", "UNIÃO": "#2445a0", "NOVO": "#f28b00",
    "PODEMOS": "#7a2f8f", "CIDADANIA": "#e8602c", "AVANTE": "#f57e20",
    "PSOL": "#e8762d", "PCdoB": "#d81b60", "PV": "#2e7d32", "PRD": "#0d6e6e",
    "SOLIDARIEDADE": "#f2a900", "REDE": "#00a1a1", "PRTB": "#6d4c41",
    "DC": "#5c6bc0", "PMB": "#8d6e63", "PSTU": "#b71c1c", "PCB": "#c62828",
    "UP": "#c62828", "AGIR": "#455a64", "MOBILIZA": "#546e7a"
  };

  function norm(s) {
    return (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().trim();
  }

  function colorFor(party) {
    if (party && PARTY_COLORS[party]) return PARTY_COLORS[party];
    // hash fallback determinístico
    var h = 0;
    var p = (party || "?");
    for (var i = 0; i < p.length; i++) h = (h * 31 + p.charCodeAt(i)) >>> 0;
    return "hsl(" + (h % 360) + ", 55%, 52%)";
  }

  function fmtMoney(v) {
    if (v == null || v === "") return "—";
    if (typeof v === "number") {
      return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    }
    var n = Number(String(v).replace(/[^\d.,-]/g, "").replace(/\./g, "").replace(",", "."));
    if (isNaN(n)) return String(v);
    return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ---------- render estado ---------- */
  function renderEstado() {
    var el = document.getElementById("panelEstado");
    if (!estado) { el.innerHTML = '<div class="empty">Carregando…</div>'; return; }
    var g = estado.governador, v = estado.vice_governador, s = estado.senadores;
    var html = "";

    html += '<div class="card"><h2>Governador</h2>';
    html += '<p class="sub">Poder Executivo estadual</p>';
    html += personRow(g.eleito.nome_urna || g.eleito.nome, g.eleito.partido, "Eleito · 2027–2030", "eleito");
    html += personRow(g.atual.nome, g.atual.partido, "Atual · até 2026", "atual");
    html += '<h3>Vice-governador</h3>';
    html += personRow(v.eleito.nome, v.eleito.partido, "Eleito · 2027–2030", "eleito");
    html += personRow(v.atual.nome, v.atual.partido, "Atual · até 2026", "atual");
    html += '</div>';

    html += '<div class="card"><h2>Senadores</h2>';
    html += '<p class="sub">3 cadeiras · Rio Grande do Sul</p><h3>Atuais</h3>';
    s.atuais.forEach(function (x) { html += personRow(x.nome, x.partido, x.mandato, "atual"); });
    html += '<h3>Eleitos em 2026 (posse 2027)</h3>';
    s.eleitos_2026.forEach(function (x) { html += personRow(x.nome_urna || x.nome, x.partido, x.mandato, "eleito"); });
    html += '</div>';

    html += '<div class="card"><h2>Assembleia e Câmara Federal</h2>';
    html += '<p class="sub">Deputados estaduais (55) e federais (31) eleitos em 2026 — cobertura em expansão.</p></div>';

    el.innerHTML = html;
  }

  function personRow(name, party, meta, kind) {
    var dot = '<span class="party-dot" style="background:' + colorFor(party) + '"></span>';
    return '<div class="person"><div><div class="name">' + dot + esc(name) + '</div>' +
      '<div class="party">' + esc(party || "") + (meta ? " · " + esc(meta) : "") + '</div></div>' +
      '<span class="badge ' + kind + '">' + (kind === "eleito" ? "eleito" : "atual") + '</span></div>';
  }

  /* ---------- render município ---------- */
  function renderMunicipio(props) {
    var el = document.getElementById("panelMunicipio");
    if (!props || !props.prefeito) {
      el.innerHTML = '<div class="empty">Clique em um município no mapa<br>ou busque pelo nome.</div>';
      return;
    }
    var html = "";
    html += '<div class="card"><h2>' + esc(props.nome) + '</h2>';
    html += '<p class="sub">IBGE ' + esc(props.codigo_ibge) + '</p>';

    html += '<h3>Prefeito(a)</h3>';
    html += personRow(props.prefeito.nome_urna || props.prefeito.nome, props.prefeito.partido, props.prefeito.mandato);
    if (props.prefeito.situacao) html += '<p class="sub">' + esc(props.prefeito.situacao) + '</p>';

    if (props.vice_prefeito) {
      html += '<h3>Vice-prefeito(a)</h3>';
      html += personRow(props.vice_prefeito.nome_urna || props.vice_prefeito.nome, props.vice_prefeito.partido, props.vice_prefeito.mandato);
      if (props.vice_prefeito.situacao) html += '<p class="sub">' + esc(props.vice_prefeito.situacao) + '</p>';
    }

    if (props.nota) html += '<p class="sub" style="margin-top:10px">⚠ ' + esc(props.nota) + '</p>';
    html += '</div>';

    // Gastos (aluguel etc.)
    if (props.gastos) {
      html += renderGastos(props.gastos);
    }

    if (props.fontes && props.fontes.length) {
      html += '<div class="card"><h2>Fontes</h2>' + props.fontes.map(function (u) {
        return '<div class="sub"><a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(u) + '</a></div>';
      }).join("") + '</div>';
    }

    el.innerHTML = html;
  }

  function renderGastos(g) {
    var html = '<div class="card"><h2>Gastos da prefeitura</h2>';
    var al = g.aluguel || {};
    if (al.titulo) html += '<p class="sub" style="margin-top:2px">' + esc(al.titulo) + '</p>';
    if (al.nota) html += '<div class="gastos-note">' + esc(al.nota) + '</div>';

    // elementos de despesa (locação é subitem)
    if (al.por_elemento && al.por_elemento.length) {
      al.por_elemento.forEach(function (el) {
        html += '<h3>' + esc(el.elemento) + '</h3><div class="gastos-grid">';
        Object.keys(el.anos || {}).forEach(function (ano) {
          html += '<div class="gastos-cell"><div class="label">' + esc(ano) + '</div>' +
            '<div class="value money">' + fmtMoney(el.anos[ano]) + '</div></div>';
        });
        html += '</div>';
      });
    }

    // locadores identificados
    var loc = al.locadores_identificados || al.maiores_locadores || [];
    if (loc.length) {
      html += '<h3>Locadores de imóveis identificados</h3>';
      html += '<table class="mini"><thead><tr><th>Credor</th><th>Valor</th></tr></thead><tbody>';
      loc.forEach(function (l) {
        html += '<tr><td>' + esc(l.credor) +
          (l.periodo ? '<div class="muted" style="font-size:11px">' + esc(l.periodo) + '</div>' : '') +
          '</td><td class="money">' + fmtMoney(l.valor) + '</td></tr>';
      });
      html += '</tbody></table>';
    }

    // fontes
    var src = al.fontes || g.fontes || [];
    if (src.length) {
      html += '<h3>Fontes</h3>' + src.map(function (u) {
        return '<div class="sub"><a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(u) + '</a></div>';
      }).join("");
    }
    if (g.bloqueios) html += '<div class="gastos-note warn">' + esc(g.bloqueios) + '</div>';
    if (g.extraido_em) html += '<p class="muted" style="font-size:11px;margin-top:8px">Dados extraídos em ' + esc(g.extraido_em) + '.</p>';
    html += '</div>';
    return html;
  }

  /* ---------- legend ---------- */
  function renderLegend() {
    var counts = {};
    features.forEach(function (f) {
      var p = f.properties.prefeito ? (f.properties.prefeito.partido || "?") : "?";
      counts[p] = (counts[p] || 0) + 1;
    });
    var parties = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
    var html = '<h4>Prefeitos por partido</h4>';
    parties.forEach(function (p) {
      html += '<div class="item"><span class="party-dot" style="background:' + colorFor(p) + '"></span>' +
        esc(p) + '<span class="count">' + counts[p] + '</span></div>';
    });
    document.getElementById("legend").innerHTML = html;
  }

  /* ---------- popup ---------- */
  function popupHTML(props) {
    var html = '<h3>' + esc(props.nome) + '</h3>';
    if (props.prefeito) {
      html += '<div><b>Prefeito:</b> ' + esc(props.prefeito.nome_urna || props.prefeito.nome) +
        ' (' + esc(props.prefeito.partido) + ')</div>';
    }
    if (props.vice_prefeito) {
      html += '<div><b>Vice:</b> ' + esc(props.vice_prefeito.nome_urna || props.vice_prefeito.nome) +
        ' (' + esc(props.vice_prefeito.partido) + ')</div>';
    }
    if (props.gastos) html += '<div style="margin-top:6px"><b>Gastos com aluguel disponíveis</b></div>';
    html += '<div style="margin-top:6px;font-size:12px;color:#94a3b8">Clique para detalhes no painel</div>';
    return html;
  }

  /* ---------- clipagem ---------- */
  var TIPO_LABELS = {
    "noticia": "Notícia",
    "comunicado": "Comunicação oficial",
    "post": "Post em rede social",
    "video": "Vídeo",
    "entrevista": "Entrevista",
    "agenda": "Agenda"
  };

  function loadClipagem() {
    fetch("clipagem/clips.json").then(function (r) { return r.json(); }).then(function (d) {
      clips = d;
      renderClipagem();
    }).catch(function () {
      document.getElementById("panelClipagem").innerHTML =
        '<div class="empty">Clipagem não encontrada.</div>';
    });
  }

  function clipagemItens() {
    var all = [];
    (clips.pessoas || []).forEach(function (p) {
      (p.itens || []).forEach(function (it) { all.push({ pessoa: p, item: it }); });
    });
    all.sort(function (a, b) {
      var da = String(a.item.data || ""), db = String(b.item.data || "");
      return da < db ? 1 : (da > db ? -1 : 0);
    });
    if (clipFilter !== "todos") all = all.filter(function (x) { return x.item.tipo === clipFilter; });
    return all;
  }

  function renderClipagem() {
    var el = document.getElementById("panelClipagem");
    if (!clips || !clips.pessoas || !clips.pessoas.length) {
      el.innerHTML = '<div class="empty">Nenhuma clipagem cadastrada ainda.</div>';
      return;
    }
    var tipos = ["todos", "noticia", "comunicado", "post", "video", "entrevista", "agenda"];
    var html = '<div class="clip-filters">' + tipos.map(function (t) {
      var label = t === "todos" ? "Todos" : TIPO_LABELS[t] || t;
      var active = clipFilter === t ? " is-active" : "";
      return '<button class="chip' + active + '" data-tipo="' + t + '">' + label + '</button>';
    }).join("") + '</div>';

    (clips.pessoas || []).forEach(function (p) {
      html += '<div class="card clip-person"><h2>' + esc(p.nome_completo || p.nome) + '</h2>';
      html += '<p class="sub">' + esc(p.cargo || "") + ' · ' + esc(p.partido || "") + '</p>';
      if (p.resumo) html += '<p class="clip-resumo">' + esc(p.resumo) + '</p>';

      var itens = (p.itens || []).slice().sort(function (a, b) {
        return String(a.data) < String(b.data) ? 1 : -1;
      });
      if (clipFilter !== "todos") itens = itens.filter(function (x) { return x.tipo === clipFilter; });

      if (!itens.length) {
        html += '<p class="sub">Sem itens deste tipo.</p>';
      } else {
        html += '<ol class="clip-list">';
        itens.forEach(function (it) { html += clipItemHTML(it); });
        html += '</ol>';
      }
      html += '</div>';
    });

    el.innerHTML = html;
    el.querySelectorAll(".chip").forEach(function (c) {
      c.addEventListener("click", function () {
        clipFilter = c.dataset.tipo;
        renderClipagem();
      });
    });
  }

  function clipItemHTML(it) {
    var tipo = it.tipo || "noticia";
    var html = '<li class="clip-item">';
    html += '<div class="clip-item__head"><span class="clip-tipo clip-tipo--' + esc(tipo) + '">' + esc(TIPO_LABELS[tipo] || tipo) + '</span>';
    html += '<span class="clip-date">' + esc(it.data || "") + '</span></div>';
    html += '<div class="clip-title"><a href="' + esc(it.url) + '" target="_blank" rel="noopener">' + esc(it.titulo) + '</a></div>';
    html += '<div class="clip-fonte">' + esc(it.fonte || "") + '</div>';
    if (it.resumo) html += '<p class="clip-resumo">' + esc(it.resumo) + '</p>';
    if (it.tags && it.tags.length) html += '<div class="clip-tags">' + it.tags.map(function (t) { return '<span class="tag">' + esc(t) + '</span>'; }).join("") + '</div>';
    html += '</li>';
    return html;
  }

  /* ---------- seleção ---------- */
  function selectFeature(layer, fit) {
    if (selected && selected._rsSelected) {
      geoLayer.resetStyle(selected);
      selected._rsSelected = false;
    }
    selected = layer;
    layer._rsSelected = true;
    layer.setStyle({ weight: 3, color: "#f8fafc", fillOpacity: 0.55 });
    if (fit) map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 12 });
    renderMunicipio(layer.feature.properties);
    showTab("municipio");
    layer.openPopup();
  }

  var TAB_PANELS = { estado: "panelEstado", municipio: "panelMunicipio", clipagem: "panelClipagem" };
  function showTab(name) {
    Object.keys(TAB_PANELS).forEach(function (k) {
      var t = document.querySelector('.tab[data-tab="' + k + '"]');
      if (t) t.classList.toggle("is-active", k === name);
      document.getElementById(TAB_PANELS[k]).hidden = (k !== name);
    });
  }

  /* ---------- init ---------- */
  function initMap() {
    map = L.map("map", { zoomControl: true }).setView([-29.9, -53.4], 7);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    geoLayer = L.geoJSON(null, {
      style: function (feat) {
        var p = feat.properties.prefeito ? feat.properties.prefeito.partido : null;
        return {
          color: "#0f172a",
          weight: 0.6,
          fillColor: colorFor(p),
          fillOpacity: 0.72
        };
      },
      onEachFeature: function (feature, layer) {
        features.push(feature);
        nameIndex[norm(feature.properties.nome)] = layer;
        layer.bindPopup(popupHTML(feature.properties));
        layer.on("click", function () { selectFeature(layer, false); });
        layer.on("mouseover", function (e) {
          if (layer !== selected) layer.setStyle({ weight: 1.6, color: "#e2e8f0" });
          layer.bringToFront();
        });
        layer.on("mouseout", function () {
          geoLayer.resetStyle(layer);
          if (layer === selected) layer.setStyle({ weight: 3, color: "#f8fafc", fillOpacity: 0.55 });
        });
      }
    }).addTo(map);
  }

  function loadData() {
    var p1 = fetch("data/estado.json").then(function (r) { return r.json(); });
    var p2 = fetch("data/municipios.geojson").then(function (r) { return r.json(); });
    Promise.all([p1, p2]).then(function (res) {
      estado = res[0];
      renderEstado();
      geoLayer.addData(res[1]);
      renderLegend();
    }).catch(function (err) {
      document.getElementById("panelEstado").innerHTML =
        '<div class="empty">Erro ao carregar dados: ' + esc(err.message) + '</div>';
    });
  }

  /* ---------- busca ---------- */
  function setupSearch() {
    var input = document.getElementById("search");
    var list = document.getElementById("searchResults");
    var keys = [];
    input.addEventListener("input", function () {
      var q = norm(input.value);
      list.innerHTML = "";
      if (q.length < 2) { list.classList.remove("is-open"); return; }
      keys = Object.keys(nameIndex).filter(function (k) { return k.indexOf(q) === 0; }).slice(0, 12);
      if (!keys.length) { list.classList.remove("is-open"); return; }
      keys.forEach(function (k) {
        var li = document.createElement("li");
        var f = nameIndex[k].feature;
        var p = f.properties.prefeito ? f.properties.prefeito.nome_urna || f.properties.prefeito.nome : "—";
        li.innerHTML = esc(f.properties.nome) + "<small>" + esc(p || "") + "</small>";
        li.addEventListener("click", function () {
          selectFeature(nameIndex[k], true);
          list.classList.remove("is-open");
          input.value = f.properties.nome;
        });
        list.appendChild(li);
      });
      list.classList.add("is-open");
    });
    input.addEventListener("blur", function () {
      setTimeout(function () { list.classList.remove("is-open"); }, 150);
    });
  }

  /* ---------- tabs e toggle ---------- */
  function setupUI() {
    document.querySelectorAll(".tab").forEach(function (t) {
      t.addEventListener("click", function () { showTab(t.dataset.tab); });
    });
    var toggle = document.getElementById("sidebarToggle");
    var sidebar = document.getElementById("sidebar");
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("is-closed");
      toggle.classList.toggle("is-shifted");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMap();
    loadData();
    loadClipagem();
    setupSearch();
    setupUI();
    renderMunicipio(null);
  });
})();
