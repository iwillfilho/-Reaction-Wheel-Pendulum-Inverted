// Abas, painel do 3D, guia de montagem (índice, mapa das tarefas, caixas) e
// esquema de ligações. Usa DADOS (gerador), REDES, ETAPAS, TAREFA_3D e Cena (cena3d.js).

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const SVGNS = 'http://www.w3.org/2000/svg';
const ARMAZEM = 'pendulo-montagem-v1';
const TAREFAS = Object.fromEntries(DADOS.tarefas.map((t) => [t.id, t]));
const TRILHA_COR = { mecanica: '#1f5ea5', eletrica: '#c46000', integracao: '#693796' };

function svg(tag, attrs = {}, pai) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (pai) pai.appendChild(e);
  return e;
}
function salvo() { try { return JSON.parse(localStorage.getItem(ARMAZEM)) || {}; } catch { return {}; } }
function salvar(d) { try { localStorage.setItem(ARMAZEM, JSON.stringify(d)); } catch { /* arquivo local sem armazenamento */ } }

// ------------------------------------------------------------------------ abas
function abrirAba(id) {
  $$('.abas button').forEach((b) => b.classList.toggle('ativa', b.dataset.aba === id));
  $$('.aba').forEach((a) => a.classList.toggle('ativa', a.id === id));
  if (id === 'aba-3d') window.dispatchEvent(new Event('resize'));
}
$$('.abas button').forEach((b) => b.addEventListener('click', () => abrirAba(b.dataset.aba)));
$('#versao').innerHTML = `gerado em ${DADOS.data}<br>versão ${DADOS.versao}`;

// --------------------------------------------------------------------- figuras
$$('img[data-fig]').forEach((img) => { img.src = DADOS.figuras[img.dataset.fig]; });
$$('img[data-tikz]').forEach((img) => { img.src = DADOS.tikz[+img.dataset.tikz]; });

// ===================================================================== 3D
Cena.init();
const legendas = { incl: $('#incl-val'), giro: $('#giro-val'), exp: $('#exp-val') };
Cena.aoMudarEstado = (e) => {
  $('#incl').value = e.incl; legendas.incl.textContent = e.incl.toFixed(1).replace('.', ',') + '°';
  $('#giro').value = e.giro; legendas.giro.textContent = Math.round(e.giro) + '°';
  $('#explodir').value = e.explodir; legendas.exp.textContent = Math.round(e.explodir * 100) + ' %';
  $('#etapa').value = e.etapa; $('#etapa-num').textContent = e.etapa + ' de 9'; $('#etapa-nome').textContent = ETAPAS[e.etapa];
  $$('#redes3d li, #redes-esq li').forEach((li) => li.classList.toggle('fixa', li.dataset.rede === e.redeFixa));
  if (!e.destaque) $('#faixa-tarefa').hidden = true;
};
Cena.definir({ etapa: 9 });
$('#etapa').addEventListener('input', (ev) => Cena.definir({ etapa: +ev.target.value, destaque: null }));
$('#incl').addEventListener('input', (ev) => { $('#balancar').checked = false; Cena.definir({ incl: +ev.target.value, balancar: false }); });
$('#giro').addEventListener('input', (ev) => { $('#girar').checked = false; Cena.definir({ giro: +ev.target.value, girar: false }); });
$('#explodir').addEventListener('input', (ev) => Cena.definir({ explodir: +ev.target.value }));
$('#balancar').addEventListener('change', (ev) => Cena.definir({ balancar: ev.target.checked, ...(ev.target.checked ? {} : { incl: 0 }) }));
$('#girar').addEventListener('change', (ev) => Cena.definir({ girar: ev.target.checked }));
$$('#vistas button').forEach((b) => b.addEventListener('click', () => Cena.vista(b.dataset.vista)));
$$('[data-camada]').forEach((c) => c.addEventListener('change', () => {
  const camadas = Object.fromEntries($$('[data-camada]').map((x) => [x.dataset.camada, x.checked]));
  Cena.definir({ camadas });
}));

function listaRedes(ul, aoClicar) {
  for (const [id, r] of Object.entries(REDES)) {
    const li = document.createElement('li');
    li.dataset.rede = id;
    li.innerHTML = `<span class="cor" style="background:${r.cor}"></span><span>${r.nome}</span>`;
    li.addEventListener('mouseenter', () => focarRede(id));
    li.addEventListener('mouseleave', () => focarRede(null));
    li.addEventListener('click', () => aoClicar(id));
    ul.appendChild(li);
  }
}
function fixarRede(id) {
  const atual = Cena.estado.redeFixa;
  Cena.definir({ redeFixa: atual === id ? null : id, destaque: null, etapa: 9 });
}
listaRedes($('#redes3d'), fixarRede);

Cena.aoSelecionar = (d) => {
  const el = $('#info-corpo');
  if (!d) { el.innerHTML = 'Clique numa peça ou num fio.'; el.className = 'nota'; return; }
  el.className = '';
  const tarefas = (d.tarefas || []).map((t) => `<a data-ir="${t}">${t}</a>`).join(', ');
  el.innerHTML = `<div class="nome">${d.nome}</div><table>${d.linhas.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('')}
    ${tarefas ? `<tr><td>Tarefas</td><td>${tarefas}</td></tr>` : ''}</table>`;
  $$('a[data-ir]', el).forEach((a) => a.addEventListener('click', () => irParaTarefa(a.dataset.ir)));
};

function mostrarTarefa3D(id) {
  const t = TAREFAS[id];
  abrirAba('aba-3d');
  Cena.destacarTarefa(id);
  const faixa = $('#faixa-tarefa');
  faixa.className = 'faixa-tarefa ' + t.trilha;
  $('#faixa-texto').innerHTML = `<b>${id}</b> ${t.titulo}`;
  faixa.dataset.tarefa = id;
  faixa.hidden = false;
}
$('#faixa-limpar').addEventListener('click', () => { Cena.definir({ destaque: null, etapa: 9 }); $('#faixa-tarefa').hidden = true; });
$('#faixa-ir').addEventListener('click', () => irParaTarefa($('#faixa-tarefa').dataset.tarefa));

$('#resumo').innerHTML = DADOS.resumo.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('');

// ============================================================ montagem física
const feitas = () => salvo().feitas || {};
function marcarFeita(id, v) {
  const d = salvo(); d.feitas = d.feitas || {}; d.feitas[id] = v; salvar(d); atualizarProgresso();
}

function irParaTarefa(id) {
  abrirAba('aba-montagem');
  const art = document.getElementById('tarefa-' + id);
  if (!art) return;
  art.classList.remove('fechada');
  art.scrollIntoView({ block: 'start', behavior: 'instant' });
  art.classList.remove('pisca'); void art.offsetWidth; art.classList.add('pisca');
}

// caixas das tarefas: abrem e fecham pelo cabeçalho; "feita" e checklists ficam salvos
$$('article.tarefa').forEach((art) => {
  const id = art.dataset.tarefa;
  art.classList.add('fechada');
  const cab = $('header', art);
  const lab = document.createElement('label');
  lab.className = 'estado';
  lab.innerHTML = `<input type="checkbox"> feita`;
  lab.addEventListener('click', (ev) => ev.stopPropagation());
  const cx = $('input', lab);
  cx.checked = !!feitas()[id];
  cx.addEventListener('change', () => marcarFeita(id, cx.checked));
  cab.insertBefore(lab, $('.ver3d', cab));
  cab.addEventListener('click', () => art.classList.toggle('fechada'));
  $('.ver3d', cab).addEventListener('click', (ev) => { ev.stopPropagation(); mostrarTarefa3D(id); });
});
(() => {
  const d = salvo().check || {};
  $$('input[data-check]').forEach((c) => {
    c.checked = !!d[c.dataset.check];
    c.addEventListener('change', () => { const s = salvo(); s.check = s.check || {}; s.check[c.dataset.check] = c.checked; salvar(s); });
  });
})();
// links internos (\ref) abrem a tarefa que contém o alvo
$$('#guia a.ref').forEach((a) => a.addEventListener('click', (ev) => {
  const alvo = document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
  if (!alvo) return;
  ev.preventDefault();
  const art = alvo.closest('article.tarefa');
  if (art) art.classList.remove('fechada');
  alvo.scrollIntoView({ block: 'center' });
}));

// índice lateral
(() => {
  const nav = $('#indice');
  const add = (html, cls, alvo, extra) => {
    const a = document.createElement('a');
    a.className = cls; a.innerHTML = html; a.href = '#' + alvo;
    if (extra) Object.assign(a.dataset, extra);
    a.addEventListener('click', (ev) => {
      ev.preventDefault();
      if (extra && extra.tarefa) irParaTarefa(extra.tarefa);
      else document.getElementById(alvo).scrollIntoView({ block: 'start' });
    });
    nav.appendChild(a);
  };
  add('Mapa das tarefas', 'sec', 'mapa');
  for (const s of DADOS.secoes) {
    add(`${s.num}. ${s.titulo}`, 'sec', s.id);
    for (const art of $$('article.tarefa', document.getElementById(s.id))) {
      const t = TAREFAS[art.dataset.tarefa];
      add(`<span class="chip ${t.trilha}">${t.id}</span><span>${t.titulo}</span>`, 'tar', art.id, { tarefa: t.id });
    }
  }
})();

// mapa das tarefas: colunas por trilha, linhas pelo nível de dependência
function desenharFluxo() {
  const nivel = {};
  const calc = (id) => nivel[id] ?? (nivel[id] = TAREFAS[id].deps.length ? 1 + Math.max(...TAREFAS[id].deps.map(calc)) : 0);
  DADOS.tarefas.forEach((t) => calc(t.id));
  const W = 138, H = 56, GX = 12, GY = 18;
  const colTrilha = { mecanica: 0, eletrica: 3, integracao: 6 };
  const ocup = {}, pos = {};
  for (const t of DADOS.tarefas) {
    const n = nivel[t.id], base = colTrilha[t.trilha];
    let c = base;
    while (ocup[c + ',' + n]) c++;
    ocup[c + ',' + n] = true;
    pos[t.id] = { x: 10 + c * (W + GX), y: 34 + n * (H + GY) };
  }
  const maxX = Math.max(...Object.values(pos).map((p) => p.x)) + W + 10;
  const maxY = Math.max(...Object.values(pos).map((p) => p.y)) + H + 10;
  const s = svg('svg', { viewBox: `0 0 ${maxX} ${maxY}`, role: 'img', 'aria-label': 'mapa das tarefas' });
  const defs = svg('defs', {}, s);
  const mk = svg('marker', { id: 'ponta', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
  svg('path', { d: 'M0,0 L10,5 L0,10 z', fill: '#9aa5b0' }, mk);
  for (const [tr, c] of Object.entries(colTrilha)) {
    const t = svg('text', { x: 10 + c * (W + GX), y: 18, 'font-weight': 700, 'font-size': 13, fill: TRILHA_COR[tr] }, s);
    t.textContent = { mecanica: 'Trilha mecânica', eletrica: 'Trilha elétrica', integracao: 'Integração' }[tr];
  }
  const setas = [];
  for (const t of DADOS.tarefas) for (const d of t.deps) {
    const a = pos[d], b = pos[t.id];
    const x1 = a.x + W / 2, y1 = a.y + H, x2 = b.x + W / 2, y2 = b.y;
    const longa = TAREFAS[d].trilha !== t.trilha && nivel[t.id] - nivel[d] > 1;
    const p = svg('path', { class: 'seta' + (longa ? ' longa' : ''), d: `M${x1},${y1} C${x1},${y1 + 26} ${x2},${y2 - 26} ${x2},${y2 - 1}`, 'marker-end': 'url(#ponta)' }, s);
    p.dataset.de = d; p.dataset.para = t.id;
    setas.push(p);
  }
  for (const t of DADOS.tarefas) {
    const g = svg('g', { class: 'no', transform: `translate(${pos[t.id].x},${pos[t.id].y})` }, s);
    g.dataset.tarefa = t.id;
    svg('rect', { width: W, height: H, rx: 5, fill: '#fff' }, g);
    svg('rect', { width: W, height: H, rx: 5, fill: TRILHA_COR[t.trilha] + '14', stroke: TRILHA_COR[t.trilha] }, g);
    const tid = svg('text', { x: 8, y: 17, class: 'id', fill: TRILHA_COR[t.trilha] }, g); tid.textContent = t.id;
    const dur = svg('text', { x: W - 8, y: 17, 'text-anchor': 'end', fill: '#56606b', 'font-size': 11 }, g); dur.textContent = t.duracao;
    // título em até 2 linhas
    const linhas = [''];
    for (const p of t.titulo.split(' ')) {
      const l = linhas[linhas.length - 1];
      if ((l + ' ' + p).trim().length > 22 && l) linhas.push(p); else linhas[linhas.length - 1] = (l + ' ' + p).trim();
    }
    if (linhas.length > 2) { linhas.length = 2; linhas[1] = linhas[1].slice(0, 20) + '…'; }
    linhas.forEach((l, k) => { svg('text', { x: 8, y: 33 + k * 14 }, g).textContent = l; });
    svg('title', {}, g).textContent = `${t.id} ${t.titulo}\nPessoas: ${t.pessoas} · Duração: ${t.duracao}\nDepende de: ${t.depende}`;
    g.addEventListener('click', () => irParaTarefa(t.id));
    g.addEventListener('mouseenter', () => {
      const rel = new Set([t.id]);
      const sobe = (id) => TAREFAS[id].deps.forEach((d) => { rel.add(d); sobe(d); });
      sobe(t.id);
      $('#fluxo').classList.add('foco');
      $$('.no', s).forEach((n) => n.classList.toggle('ativo', rel.has(n.dataset.tarefa)));
      setas.forEach((p) => p.classList.toggle('ativa', rel.has(p.dataset.para) && rel.has(p.dataset.de)));
    });
    g.addEventListener('mouseleave', () => $('#fluxo').classList.remove('foco'));
  }
  $('#fluxo').appendChild(s);
}
desenharFluxo();

function atualizarProgresso() {
  const f = feitas();
  const n = DADOS.tarefas.filter((t) => f[t.id]).length;
  $('#progresso').innerHTML = `${n} de ${DADOS.tarefas.length} tarefas marcadas como feitas<div class="barra"><div style="width:${100 * n / DADOS.tarefas.length}%"></div></div>`;
  $$('#fluxo .no').forEach((g) => g.classList.toggle('feita', !!f[g.dataset.tarefa]));
  $$('#indice a.tar').forEach((a) => a.classList.toggle('feita', !!f[a.dataset.tarefa]));
}
atualizarProgresso();

// ================================================================== ligações
// Esquema desenhado à mão a partir de docs/ligacoes.md e do guia (figuras de
// alimentação, pinagem e placa perfurada). A Black Pill aparece girada 180°:
// a fileira de baixo (B0, B1, B10, A2–A4) fica para cima, perto do IBT-2.
const PINO_REDE = { PB0: 'ibt', PB1: 'ibt', PB10: 'ibt', PA15: 'enc', PB3: 'enc', PB6: 'i2c', PB7: 'i2c', PA2: 'serial', PA3: 'serial', PA4: 'vbus' };
let focoEsq = null;
function focarRede(id) {
  Cena.definir({ redeFoco: id });
  const s = $('#esquema svg');
  if (s) {
    s.classList.toggle('foco', !!id);
    $$('.fio, .no-e', s).forEach((p) => p.classList.toggle('ativo', p.dataset.rede === id));
  }
  $$('#tab-pinagem tr').forEach((tr) => tr.classList.toggle('foco', !!id && tr.dataset.rede === id));
  focoEsq = id;
}
function verRedeNo3D(id) {
  abrirAba('aba-3d');
  Cena.definir({ redeFixa: id, redeFoco: null, destaque: null, etapa: 9, explodir: 0 });
}

function desenharEsquema() {
  const s = svg('svg', { viewBox: '0 0 1140 640', role: 'img', 'aria-label': 'esquema de ligações' });
  const G = { fios: svg('g', {}, s), blocos: svg('g', {}, s), nos: svg('g', {}, s) };
  const txt = (x, y, t, o = {}, pai = G.blocos) => { const e = svg('text', Object.assign({ x, y }, o), pai); e.textContent = t; return e; };
  const bloco = (x, y, w, h, titulo, sub) => {
    const g = svg('g', { class: 'bloco-e' }, G.blocos);
    svg('rect', { x, y, width: w, height: h, rx: 6, class: 'corpo' }, g);
    txt(x + w / 2, y + 18, titulo, { class: 'tit', 'text-anchor': 'middle' }, g);
    if (sub) sub.split('\n').forEach((l, k) => txt(x + w / 2, y + 33 + k * 13, l, { class: 'pq', 'text-anchor': 'middle' }, g));
    return g;
  };
  const fio = (rede, pts, o = {}) => {
    const d = 'M' + pts.map((p) => p.join(',')).join(' L');
    const cor = o.cor || REDES[rede].cor;
    const p = svg('path', { d, class: 'fio' + (o.grosso ? ' grosso' : ''), stroke: cor, ...(o.tracejado ? { 'stroke-dasharray': '5 4' } : {}) }, G.fios);
    p.dataset.rede = rede;
    const alvo = svg('path', { d, class: 'alvo' }, G.fios);
    for (const el of [p, alvo]) {
      el.addEventListener('mouseenter', () => focarRede(rede));
      el.addEventListener('mouseleave', () => focarRede(null));
      el.addEventListener('click', () => verRedeNo3D(rede));
    }
    if (o.rotulo) txt(o.rotulo[0], o.rotulo[1], o.rotulo[2], { class: 'pq', fill: cor }, G.blocos);
    return p;
  };
  const no = (rede, x, y) => { const c = svg('circle', { cx: x, cy: y, r: 3.6, class: 'no-e', fill: REDES[rede].cor }, G.nos); c.dataset.rede = rede; };
  const etiqueta = (rede, x, y, t, ancora = 'middle') => {
    const e = txt(x, y, t, { class: 'pq', 'text-anchor': ancora, 'font-weight': 700, style: 'fill:' + REDES[rede].cor });
    e.classList.add('no-e'); e.dataset.rede = rede;
  };
  const resistor = (x, y1, y2, rotulo, rede, esq) => {
    const ym = (y1 + y2) / 2;
    svg('rect', { x: x - 6, y: ym - 15, width: 12, height: 30, fill: '#fff', stroke: REDES[rede].cor, 'stroke-width': 1.8 }, G.blocos);
    txt(esq ? x - 10 : x + 10, ym + 4, rotulo, { class: 'pq', 'text-anchor': esq ? 'end' : 'start' });
  };
  const capacitor = (x, y1, y2, rotulo, rede) => {
    const ym = (y1 + y2) / 2, c = REDES[rede].cor;
    svg('rect', { x: x - 10, y: ym - 4, width: 20, height: 8, fill: '#fff', stroke: 'none' }, G.blocos);
    svg('line', { x1: x - 9, y1: ym - 3, x2: x + 9, y2: ym - 3, stroke: c, 'stroke-width': 2 }, G.blocos);
    svg('line', { x1: x - 9, y1: ym + 3, x2: x + 9, y2: ym + 3, stroke: c, 'stroke-width': 2 }, G.blocos);
    txt(x + 12, ym + 4, rotulo, { class: 'pq' });
  };

  // ---------------------------------------------------------------- potência
  const yV = 85, yG = 250;
  bloco(30, 55, 100, 115, 'Fonte 12 V', '10 A ou mais\n(fora da base)');
  txt(122, yV + 4, '+', { 'text-anchor': 'end', 'font-weight': 700 }); txt(122, 149, '−', { 'text-anchor': 'end', 'font-weight': 700 });
  svg('rect', { x: 165, y: yV - 9, width: 52, height: 18, rx: 9, fill: '#fff', stroke: '#48535e' }, G.blocos);
  txt(191, yV + 4, '10 A', { class: 'pq', 'text-anchor': 'middle' }); txt(191, yV - 14, 'fusível', { class: 'pq', 'text-anchor': 'middle' });
  bloco(600, 50, 150, 240, 'IBT-2', 'BTS7960');
  txt(606, yV + 4, 'B+', { class: 'pq' }); txt(606, yG + 4, 'B−', { class: 'pq' });
  txt(744, 114, 'M+', { class: 'pq', 'text-anchor': 'end' }); txt(744, 174, 'M−', { class: 'pq', 'text-anchor': 'end' });
  const hdr = ['GND', 'VCC', 'L_IS', 'R_IS', 'L_EN', 'R_EN', 'LPWM', 'RPWM'];
  const hx = (n) => 615 + hdr.indexOf(n) * 17;
  hdr.forEach((n) => { svg('rect', { x: hx(n) - 3, y: 286, width: 6, height: 6, fill: '#333' }, G.blocos); txt(hx(n), 280, n, { class: 'pq', 'text-anchor': 'end', transform: `rotate(-90 ${hx(n)} 280)` }); });
  svg('circle', { cx: 880, cy: 140, r: 34, fill: '#f6f8fa', stroke: '#48535e', 'stroke-width': 1.2 }, G.blocos);
  txt(880, 147, 'M', { 'text-anchor': 'middle', 'font-size': 20, 'font-weight': 700 });
  txt(880, 192, 'motor 775', { 'text-anchor': 'middle', class: 'tit' });
  txt(880, 206, '+ 3 × 100 nF soldados nele', { 'text-anchor': 'middle', class: 'pq' });
  bloco(430, 118, 110, 72, 'Proteção', '2 × 4700 µF/35 V\n100 nF · TVS SMBJ15A');
  bloco(200, 296, 130, 68, 'Buck', '12 V → 5,0 V\n(ajustar antes de ligar)');

  fio('v12', [[130, yV], [165, yV]], { grosso: true });
  fio('v12', [[217, yV], [600, yV]], { grosso: true });
  fio('v12', [[245, yV], [245, 296]], { grosso: true }); no('v12', 245, yV);
  fio('v12', [[485, yV], [485, 118]], { grosso: true }); no('v12', 485, yV);
  fio('gnd', [[130, 145], [150, 145], [150, yG], [600, yG]], { grosso: true });
  fio('gnd', [[290, yG], [290, 296]], { grosso: true }); no('gnd', 290, yG);
  fio('gnd', [[485, 190], [485, yG]], { grosso: true }); no('gnd', 485, yG);
  txt(560, yG + 16, 'estrela no B−', { class: 'pq', 'text-anchor': 'middle' });
  txt(241, 290, 'IN+', { class: 'pq', 'text-anchor': 'end' }); txt(294, 290, 'IN−', { class: 'pq' });
  fio('motor', [[750, 110], [800, 110], [800, 126], [849, 126]], { grosso: true, cor: '#c62828' });
  fio('motor', [[750, 170], [800, 170], [800, 154], [849, 154]], { grosso: true, cor: '#22272b' });

  // ------------------------------------------------------------- Black Pill
  const xBP = (i) => 462 + i * 20;
  const topo = ['5V', 'G', '3V3', 'B10', 'B2', 'B1', 'B0', 'A7', 'A6', 'A5', 'A4', 'A3', 'A2', 'A1', 'A0', 'R', 'C15', 'C14', 'C13', 'VB'];
  const base = ['3V3', 'G', '5V', 'B9', 'B8', 'B7', 'B6', 'B5', 'B4', 'B3', 'A15', 'A12', 'A11', 'A10', 'A9', 'A8', 'B15', 'B14', 'B13', 'B12'];
  const yT = 420, yB = 500;
  const gbp = svg('g', {}, G.blocos);
  svg('rect', { x: 432, y: yT, width: 426, height: yB - yT, rx: 4, fill: '#16357d' }, gbp);
  svg('rect', { x: 855, y: yT + 25, width: 14, height: 30, rx: 3, fill: '#b9bec4' }, gbp);
  txt(862, yT + 70, 'USB-C', { class: 'pq', 'text-anchor': 'middle' }, gbp);
  txt(650, 465, 'Black Pill STM32F411 (vista de cima, girada 180°)', { 'text-anchor': 'middle', style: 'fill:#fff', 'font-weight': 600 }, gbp);
  const pinoBP = (n, x, y, cimaLbl) => {
    const nome = n.length > 1 && /^[AB]\d/.test(n) ? 'P' + n : null;
    const rede = nome ? PINO_REDE[nome] : null;
    const r = svg('rect', { x: x - 6, y: y - 6, width: 12, height: 12, rx: 2, fill: rede ? REDES[rede].cor : '#c9ced4', class: 'pin-bp' }, gbp);
    const t = txt(x, cimaLbl ? y + 19 : y - 10, n, { class: 'pino', 'text-anchor': 'middle' }, gbp);
    if (rede) {
      for (const el of [r, t]) {
        el.addEventListener('mouseenter', () => focarRede(rede));
        el.addEventListener('mouseleave', () => focarRede(null));
        el.addEventListener('click', () => verRedeNo3D(rede));
      }
      svg('title', {}, r).textContent = nome;
    }
  };
  topo.forEach((n, i) => pinoBP(n, xBP(i), yT, true));
  base.forEach((n, i) => pinoBP(n, xBP(i), yB, false));
  const xT = (n) => xBP(topo.indexOf(n)), xB = (n) => xBP(base.indexOf(n));
  // SWD na ponta esquerda (com a placa girada)
  ['3V3', 'DIO', 'CLK', 'GND'].forEach((n, k) => {
    svg('rect', { x: 432, y: yT + 14 + k * 16 - 4, width: 8, height: 8, fill: '#e3c94a' }, gbp);
    txt(424, yT + 11 + k * 16, n, { class: 'pq', 'text-anchor': 'end' }, gbp);
  });

  // 5V e GND do buck
  txt(337, 322, 'OUT+', { class: 'pq' }); txt(337, 352, 'OUT−', { class: 'pq' });
  fio('v5', [[330, 330], [xT('5V'), 330], [xT('5V'), yT - 6]]);
  fio('gnd', [[330, 356], [xT('G'), 356], [xT('G'), yT - 6]]);
  fio('v33', [[xT('3V3'), yT - 6], [xT('3V3'), 392]]); etiqueta('v33', xT('3V3') + 2, 386, '3V3', 'start');
  // IBT-2: PB10 (EN), PB1 (LPWM), PB0 (RPWM)
  fio('ibt', [[xT('B10'), yT - 6], [xT('B10'), 322], [hx('L_EN'), 322], [hx('L_EN'), 292]]);
  fio('ibt', [[hx('L_EN'), 306], [hx('R_EN'), 306], [hx('R_EN'), 292]]); no('ibt', hx('L_EN'), 306); no('ibt', hx('L_EN'), 322);
  fio('ibt', [[xT('B1'), yT - 6], [xT('B1'), 336], [hx('LPWM'), 336], [hx('LPWM'), 292]]);
  fio('ibt', [[xT('B0'), yT - 6], [xT('B0'), 350], [hx('RPWM'), 350], [hx('RPWM'), 292]]);
  fio('ibt', [[xT('B10') + 22, 322], [xT('B10') + 22, 300]]); no('ibt', xT('B10') + 22, 322);
  svg('rect', { x: xT('B10') + 16, y: 296, width: 12, height: 22, fill: '#fff', stroke: REDES.ibt.cor, 'stroke-width': 1.8 }, G.blocos);
  txt(xT('B10') + 30, 306, '10 k', { class: 'pq' }); etiqueta('gnd', xT('B10') + 22, 291, 'GND');
  for (const [n, rede, t] of [['VCC', 'v33', '3V3'], ['GND', 'gnd', 'GND']]) {
    fio(rede, [[hx(n), 292], [hx(n), 298]]);
    const e = txt(hx(n) - 3, 300, t, { class: 'pq', 'font-weight': 700, style: 'fill:' + REDES[rede].cor, transform: `rotate(90 ${hx(n) - 3} 300)` });
    e.classList.add('no-e'); e.dataset.rede = rede;
  }
  txt(708, 372, 'R_IS e L_IS: opcionais (PA5, PA6)', { class: 'pq' });

  // serial (A2 = TX da placa, A3 = RX) e divisor (A4)
  bloco(905, 282, 112, 112, 'USB-serial', 'adaptador de 3,3 V\nVCC sem ligar');
  txt(912, 346, 'GND', { class: 'pq' }); txt(912, 364, 'TX → PA3', { class: 'pq' }); txt(912, 384, 'RX ← PA2', { class: 'pq' });
  fio('serial', [[xT('A2'), yT - 6], [xT('A2'), 380], [905, 380]]);
  fio('serial', [[xT('A3'), yT - 6], [xT('A3'), 392], [890, 392], [890, 360], [905, 360]]);
  fio('gnd', [[905, 342], [892, 342]]); etiqueta('gnd', 888, 346, 'GND', 'end');
  const xD = 1066;
  fio('vbus', [[570, yV], [570, 30], [xD, 30], [xD, 405]]); no('vbus', 570, yV);
  resistor(xD, 130, 190, '10 k', 'vbus');
  fio('vbus', [[xT('A4'), yT - 6], [xT('A4'), 405], [xD, 405]]); no('vbus', xD, 405);
  fio('vbus', [[xD, 405], [xD, 470]]); resistor(xD, 415, 465, '2,2 k', 'vbus', true); etiqueta('gnd', xD, 486, 'GND');
  fio('vbus', [[xD, 405], [xD + 30, 405], [xD + 30, 470]]); capacitor(xD + 30, 425, 455, '100 nF', 'vbus'); etiqueta('gnd', xD + 30, 486, 'GND');
  txt(xD - 8, 50, 'do B+', { class: 'pq', 'text-anchor': 'end' });
  txt(xD + 6, 420 - 22, 'PA4', { class: 'pq' });

  // MPU6050 e sensores (fileira de cima da placa, aqui embaixo)
  bloco(470, 560, 130, 66, 'MPU6050', 'GY-521, atrás do braço');
  fio('i2c', [[xB('B7'), yB + 6], [xB('B7'), 560]], { cor: '#7cc47f' });
  fio('i2c', [[xB('B6'), yB + 6], [xB('B6'), 560]]);
  txt(xB('B7') + 4, 552, 'SDA', { class: 'pq' }); txt(xB('B6') + 4, 540, 'SCL', { class: 'pq' });
  fio('v33', [[488, 560], [488, 544]]); etiqueta('v33', 488, 539, '3V3');
  fio('gnd', [[506, 560], [506, 548]]); etiqueta('gnd', 512, 539, 'GND', 'start');
  bloco(630, 560, 150, 66, 'Sensores ópticos', 'A e B, saída D0\nembaixo da roda');
  fio('enc', [[xB('B3'), yB + 6], [xB('B3'), 560]], { cor: '#ce93d8' });
  fio('enc', [[xB('A15'), yB + 6], [xB('A15'), 560]]);
  txt(xB('B3') - 4, 552, 'B', { class: 'pq', 'text-anchor': 'end' }); txt(xB('A15') + 4, 552, 'A', { class: 'pq' });
  fio('v33', [[740, 560], [740, 544]]); etiqueta('v33', 740, 539, '3V3');
  fio('gnd', [[762, 560], [762, 548]]); etiqueta('gnd', 768, 539, 'GND', 'start');

  // ST-Link no SWD
  bloco(230, 410, 120, 92, 'ST-Link V2', 'gravação\n3V3 só sem o buck');
  ['3V3', 'DIO', 'CLK', 'GND'].forEach((n, k) => {
    const y = yT + 14 + k * 16;
    const rede = { '3V3': 'v33', DIO: 'swd', CLK: 'swd', GND: 'gnd' }[n];
    fio(rede, [[350, y], [432, y]], n === '3V3' ? { tracejado: true, cor: '#b0b7bf' } : (n === 'CLK' ? { cor: '#7a6a00' } : {}));
  });

  $('#esquema').appendChild(s);
}
desenharEsquema();
listaRedes($('#redes-esq'), verRedeNo3D);

// tabelas de docs/ligacoes.md
function tabela(el, t, linhaExtra) {
  const thead = '<thead><tr>' + t.cab.map((c) => `<th>${c}</th>`).join('') + '</tr></thead>';
  const corpo = t.linhas.map((l) => `<tr${linhaExtra ? linhaExtra(l) : ''}>` + l.map((c) => `<td>${c}</td>`).join('') + '</tr>').join('');
  el.innerHTML = `<table>${thead}<tbody>${corpo}</tbody></table>`;
}
tabela($('#tab-pinagem'), DADOS.ligacoes.pinagem, (l) => {
  const pino = l[0].replace(/<[^>]+>/g, '');
  return PINO_REDE[pino] ? ` data-rede="${PINO_REDE[pino]}"` : '';
});
$$('#tab-pinagem tr[data-rede]').forEach((tr) => {
  tr.style.cursor = 'pointer';
  tr.addEventListener('mouseenter', () => focarRede(tr.dataset.rede));
  tr.addEventListener('mouseleave', () => focarRede(null));
  tr.addEventListener('click', () => verRedeNo3D(tr.dataset.rede));
});
tabela($('#tab-modulos'), DADOS.ligacoes.modulos);
tabela($('#tab-led'), DADOS.ligacoes.led);
$('#regras').innerHTML = DADOS.ligacoes.regras.map((r) => `<li>${r}</li>`).join('');

// abre direto numa aba pelo endereço (#montagem, #ligacoes)
if (location.hash === '#montagem') abrirAba('aba-montagem');
if (location.hash === '#ligacoes') abrirAba('aba-ligacoes');
