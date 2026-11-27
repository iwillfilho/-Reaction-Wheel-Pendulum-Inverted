// Cena 3D do pêndulo: peças do CAD (cad/visualizacao.scad), eletrônica e fios.
// Referencial do CAD: X para o lado, Y ao longo do pivô (+Y = frente, lado da roda),
// Z para cima, origem no pivô, milímetros.

const REDES = {
  v12:    { nome: '+12 V: fonte, fusível, B+ e buck', cor: '#d32f2f' },
  gnd:    { nome: 'GND: estrela no B− do IBT-2', cor: '#263238' },
  motor:  { nome: 'Motor: M+ e M− (14 AWG trançado)', cor: '#9b2226' },
  v5:     { nome: '5 V: buck → pino 5V da Black Pill', cor: '#c2185b' },
  v33:    { nome: '3V3 da lógica', cor: '#f06292' },
  i2c:    { nome: 'I2C do MPU6050 (PB6, PB7)', cor: '#2e7d32' },
  enc:    { nome: 'Encoder óptico (PA15, PB3)', cor: '#8e24aa' },
  ibt:    { nome: 'IBT-2: PWM e EN (PB0, PB1, PB10)', cor: '#1565c0' },
  vbus:   { nome: 'Divisor da tensão do barramento (PA4)', cor: '#8d6e63' },
  serial: { nome: 'Serial da telemetria (PA2, PA3)', cor: '#ef8f00' },
  swd:    { nome: 'SWD do ST-Link (gravação)', cor: '#c9a400' },
};

const ETAPAS = [
  null,
  'Braço com os 2 rolamentos (M6, parte 1)',
  'Motor no braço (M6, parte 3)',
  'Flange no eixo do motor (M6, parte 4)',
  'Roda com os 12 parafusos M8 (M7)',
  'Sensores ópticos e MPU6050 (M8)',
  'Base, almofadas e bandeja (M9)',
  'Pivô: a barra entra pela frente (M10)',
  'Mecânica completa, com a proteção (M10 e I5)',
  'Eletrônica na bandeja e toda a fiação (E1–E6, I1)',
];

// o que cada tarefa do guia mostra no 3D: etapa, peças e redes em destaque
const TAREFA_3D = {
  M1: { etapa: 9, pecas: ['roda', 'braco', 'suporte_sensores', 'base', 'bandeja', 'tpu'] },
  M2: { etapa: 9, pecas: ['roda', 'motor', 'flange', 'parafusos_m8', 'suporte_sensores', 'sensores', 'mpu'] },
  M3: { etapa: 8, pecas: ['barra_colares', 'protecao'] },
  M4: { etapa: 9, pecas: ['roda', 'braco', 'base'] },
  M5: { etapa: 9, pecas: ['motor', 'capsmotor'], redes: ['motor'] },
  M6: { etapa: 3, pecas: ['braco', 'rolamentos', 'motor', 'flange'] },
  M7: { etapa: 4, pecas: ['roda', 'parafusos_m8'] },
  M8: { etapa: 5, pecas: ['suporte_sensores', 'sensores', 'mpu'] },
  M9: { etapa: 6, pecas: ['base', 'bandeja', 'tpu'] },
  M10: { etapa: 7, pecas: ['barra_colares', 'rolamentos'] },
  E1: { etapa: 9, pecas: ['blackpill', 'stlink', 'serialusb', 'mpu', 'sensores'], redes: ['i2c', 'enc', 'serial', 'swd'] },
  E2: { etapa: 9, pecas: ['placa', 'blackpill'] },
  E3: { etapa: 9, pecas: ['placa', 'blackpill'], redes: ['vbus'] },
  E4: { etapa: 9, pecas: ['fonte', 'fusivel', 'ibt2', 'protecao_bus'], redes: ['v12', 'gnd'] },
  E5: { etapa: 9, pecas: ['buck', 'placa'], redes: ['v5', 'v12'] },
  E6: { etapa: 9, pecas: [], redes: ['i2c', 'enc'], extra: (o) => o.userData.chicote === 'sinal' },
  I1: { etapa: 9, pecas: ['bandeja', 'ibt2', 'buck', 'placa', 'blackpill', 'protecao_bus'], redes: Object.keys(REDES) },
  I2: { etapa: 9, pecas: [], redes: Object.keys(REDES) },
  I3: { etapa: 9, pecas: ['blackpill', 'mpu', 'sensores', 'roda'], redes: ['i2c', 'enc', 'vbus'] },
  I4: { etapa: 9, pecas: ['motor', 'ibt2', 'flange'], redes: ['motor', 'ibt'] },
  I5: { etapa: 9, pecas: ['protecao'] },
  I6: { etapa: 9, pecas: [] },
};

const Cena = (() => {
  const C = DADOS.cotas;
  const M = DADOS.massas;
  const yb = C.y_bandeja;                                       // centro da bandeja (Y)
  const zT = C.z_base + C.bandeja_altura + C.bandeja_esp;       // topo da bandeja
  const zMesa = C.z_base - 6;                                   // embaixo da base
  const zMod = zT + 6;                                          // base das placas (espaçadores de 6 mm)
  const zPino = zMod + 1.6 + 8.5;                               // topo das barras de pinos

  // ------------------------------------------------------------ descrição das peças
  const PECAS = {
    base:             { nome: 'Base', tipo: 'impressa', massa: M.base, tarefas: ['M4', 'M9'], cor: 0x778899, grupo: 'estatico', camada: 'impressas' },
    bandeja:          { nome: 'Bandeja da eletrônica', tipo: 'impressa', massa: M.bandeja, tarefas: ['M9', 'I1'], cor: 0x2f4f4f, grupo: 'estatico', camada: 'impressas' },
    tpu:              { nome: 'Almofadas de TPU (2)', tipo: 'impressa', massa: M.batente_tpu, tarefas: ['M9'], cor: 0x1c1c1c, grupo: 'estatico', camada: 'impressas' },
    barra_colares:    { nome: 'Barra de 8 mm × 82 mm e 2 colares SCC8', tipo: 'comprada', tarefas: ['M3', 'M10'], cor: 0xc0c0c0, metal: true, grupo: 'barra', camada: 'compradas', exp: [0, 160, 0] },
    protecao:         { nome: 'Proteção de policarbonato (230 × 230 mm)', tipo: 'comprada', tarefas: ['M3', 'I5'], cor: 0xbfeff5, vidro: true, grupo: 'estatico', camada: 'protecao', exp: [0, 110, 0] },
    braco:            { nome: 'Braço', tipo: 'impressa', massa: M.braco, tarefas: ['M4', 'M6'], cor: 0x4682b4, grupo: 'braco', camada: 'impressas' },
    suporte_sensores: { nome: 'Suporte dos sensores', tipo: 'impressa', massa: M.suporte_sensores, tarefas: ['M8'], cor: 0xe2b714, grupo: 'braco', camada: 'impressas', exp: [0, 45, -30] },
    motor:            { nome: 'Motor 775 (12 V)', tipo: 'comprada', tarefas: ['M2', 'M5', 'M6'], cor: 0xb5b9bd, metal: true, grupo: 'braco', camada: 'compradas', exp: [0, -80, 0] },
    sensores:         { nome: 'Sensores ópticos de fenda (2, LM393)', tipo: 'comprada', tarefas: ['M8', 'E1'], cor: 0x555a60, grupo: 'braco', camada: 'compradas', exp: [0, 45, -14] },
    mpu:              { nome: 'MPU6050 (GY-521)', tipo: 'comprada', tarefas: ['M8', 'E1'], cor: 0x4169e1, grupo: 'braco', camada: 'compradas', exp: [0, -40, 0] },
    rolamentos:       { nome: 'Rolamentos 608-ZZ (2)', tipo: 'comprada', tarefas: ['M6'], cor: 0xa9adb2, metal: true, grupo: 'braco', camada: 'compradas' },
    roda:             { nome: 'Roda (com o anel dentado do encoder)', tipo: 'impressa', massa: M.roda, tarefas: ['M4', 'M7'], cor: 0xe8860c, grupo: 'roda', camada: 'impressas', exp: [0, 80, 0] },
    flange:           { nome: 'Mini flange para eixo de 5 mm', tipo: 'comprada', tarefas: ['M6'], cor: 0xd0d3d6, metal: true, grupo: 'roda', camada: 'compradas', exp: [0, 40, 0] },
    parafusos_m8:     { nome: '12 conjuntos M8 × 16 (massa da roda)', tipo: 'comprada', tarefas: ['M2', 'M7'], cor: 0x9fa4a9, metal: true, grupo: 'roda', camada: 'compradas', exp: [0, 125, 0] },
  };
  const ELETRONICA = {
    ibt2:         { nome: 'Ponte H IBT-2 (BTS7960)', tarefas: ['E4', 'I1', 'I4'] },
    protecao_bus: { nome: 'Proteção do barramento: 2 × 4700 µF/35 V, 100 nF e TVS SMBJ15A', tarefas: ['E4'] },
    buck:         { nome: 'Conversor buck 12 V → 5,0 V', tarefas: ['E5'] },
    placa:        { nome: 'Placa perfurada (soquete, conectores, divisor, pull-down)', tarefas: ['E2', 'E3'] },
    blackpill:    { nome: 'WeAct Black Pill STM32F411CEU6', tarefas: ['E1', 'I3'] },
    fonte:        { nome: 'Fonte 12 V, 10 A ou mais (fora da base)', tarefas: ['E4'] },
    fusivel:      { nome: 'Fusível de 10 A retardado, logo depois da fonte', tarefas: ['E4'] },
    serialusb:    { nome: 'Adaptador USB-serial de 3,3 V (telemetria)', tarefas: ['E1'] },
    stlink:       { nome: 'ST-Link V2 (gravação)', tarefas: ['E1'] },
    capsmotor:    { nome: '3 capacitores de 100 nF soldados no motor', tarefas: ['M5'] },
  };

  let renderer, camera, controls, scene, raycaster, ponteiro;
  let gEst, gBarra, gBraco, gRodaPivo, gEletr, gFios, gFiosBraco;
  const pegaveis = [];           // objetos que respondem a clique
  const objPeca = {};            // nome -> mesh
  const estado = {
    etapa: 9, incl: 0, giro: 0, explodir: 0, balancar: false, girar: false,
    camadas: { impressas: true, compradas: true, protecao: true, eletronica: true, fios: true },
    destaque: null,              // {pecas:Set, redes:Set, extra}
    redeFoco: null, redeFixa: null, selecionado: null,
  };
  let aoSelecionar = () => {};
  let ultimoInclFios = null;
  let animCam = null;

  // -------------------------------------------------------------------- malhas
  function buf(b64) {
    const s = atob(b64), u = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
    return u.buffer;
  }
  function geometriaPeca(d) {
    let g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buf(d.p)), 3));
    g.setIndex(new THREE.BufferAttribute(d.i32 ? new Uint32Array(buf(d.i)) : new Uint16Array(buf(d.i)), 1));
    const arestas = new THREE.EdgesGeometry(g, 28);
    g = g.toNonIndexed();
    g.computeVertexNormals();
    return [g, arestas];
  }
  function material(cor, o = {}) {
    return new THREE.MeshStandardMaterial({
      color: cor, metalness: o.metal ? 0.55 : 0.05, roughness: o.metal ? 0.35 : 0.62,
      transparent: true, opacity: o.vidro ? 0.28 : 1, depthWrite: !o.vidro, side: o.vidro ? THREE.DoubleSide : THREE.FrontSide,
    });
  }
  function registrar(obj, dados) {
    obj.userData = Object.assign(obj.userData || {}, dados);
    obj.userData.opacidade = obj.material.opacity;
    obj.userData.depth = obj.material.depthWrite;
    pegaveis.push(obj);
    return obj;
  }

  function criarPecas() {
    for (const [nome, info] of Object.entries(PECAS)) {
      const [g, arestas] = geometriaPeca(DADOS.pecas[nome]);
      const mesh = new THREE.Mesh(g, material(info.cor, info));
      if (!info.vidro) {
        const lin = new THREE.LineSegments(arestas, new THREE.LineBasicMaterial({ color: 0x1b2430, transparent: true, opacity: 0.22 }));
        lin.raycast = () => {};
        mesh.add(lin);
      }
      registrar(mesh, { chave: nome, peca: info, camada: info.camada });
      objPeca[nome] = mesh;
      ({ estatico: gEst, barra: gBarra, braco: gBraco, roda: gRodaPivo.children[0] })[info.grupo].add(mesh);
    }
  }

  // ---------------------------------------------------------- eletrônica (caixas)
  function caixa(chave, w, d, h, cor, x, y, z, o = {}) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, d, h), material(cor, o));
    m.position.set(x, y, z);
    registrar(m, { chave, eletr: ELETRONICA[chave], camada: 'eletronica' });
    (o.pai || gEletr).add(m);
    return m;
  }
  function cilindro(chave, r, h, cor, x, y, z, eixo = 'z', o = {}) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 24), material(cor, o));
    if (eixo === 'z') m.rotation.x = Math.PI / 2;
    if (eixo === 'x') m.rotation.z = Math.PI / 2;
    m.position.set(x, y, z);
    registrar(m, { chave, eletr: ELETRONICA[chave], camada: 'eletronica' });
    (o.pai || gEletr).add(m);
    return m;
  }
  function barraPinos(chave, x, y0, n, passo, eixo = 'y') {
    const L = n * 2.54;
    const cx = eixo === 'x' ? x + (n - 1) * passo / 2 : x;
    const cy = eixo === 'y' ? y0 - (n - 1) * passo / 2 : y0;
    caixa(chave, eixo === 'x' ? L : 2.5, eixo === 'y' ? L : 2.5, 8.5, 0x111111, cx, cy, zMod + 1.6 + 4.25);
  }
  // posições dos pinos (topo) usadas pelos fios
  const P = {};
  function pinosEmY(nome, x, y0, nomes) { nomes.forEach((n, k) => { P[nome + '.' + n] = [x, y0 - k * 2.54, zPino]; }); }

  function criarEletronica() {
    // ---- IBT-2: placa 50 × 50, dissipador, bornes no lado -X, conector de sinal no lado +X
    const xI = -46;
    caixa('ibt2', 50, 50, 1.6, 0x7c2025, xI, yb, zMod + 0.8);
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) cilindro('ibt2', 2.2, 6, 0xd0c08a, xI + sx * 21, yb + sy * 21, zT + 3);
    caixa('ibt2', 40, 40, 3, 0x1d1d1d, xI, yb, zMod + 1.6 + 1.5);
    for (let k = 0; k < 9; k++) caixa('ibt2', 1.6, 40, 19, 0x262626, xI - 17.6 + k * 4.4, yb, zMod + 1.6 + 3 + 9.5);
    caixa('ibt2', 8, 15, 10, 0x2a7d4f, xI - 21, yb + 17, zMod + 1.6 + 5);     // bornes M+ M−
    caixa('ibt2', 8, 15, 10, 0x2a7d4f, xI - 21, yb - 13, zMod + 1.6 + 5);     // bornes B+ B−
    const zB = zMod + 1.6 + 4;
    P['M+'] = [xI - 25, yb + 20.5, zB]; P['M-'] = [xI - 25, yb + 13.5, zB];
    P['B+'] = [xI - 25, yb - 9.5, zB];  P['B-'] = [xI - 25, yb - 16.5, zB];
    for (const k of ['M+', 'M-', 'B+', 'B-']) cilindro('ibt2', 1.6, 2, 0xcfd3d6, xI - 21, P[k][1], zMod + 1.6 + 10.5, 'z', { metal: true });
    barraPinos('ibt2', -23.2, yb + 8.89, 8, 2.54);
    pinosEmY('IBT', -23.2, yb + 8.89, ['RPWM', 'LPWM', 'R_EN', 'L_EN', 'R_IS', 'L_IS', 'VCC', 'GND']);

    // ---- proteção do barramento: em pé, encostada nos bornes B+ e B−
    const xP = -86, yP = yb - 13, zP = C.z_base - 6 + 13;
    caixa('protecao_bus', 1.6, 34, 24, 0xc9a55a, xP, yP, zP);
    for (const s of [-1, 1]) cilindro('protecao_bus', 7.5, 22, 0x1f3d7a, xP - 11.8, yP + s * 8.5, zP - 3, 'x');
    caixa('protecao_bus', 3, 5.5, 4, 0x151515, xP - 2.3, yP, zP + 8);          // TVS
    cilindro('protecao_bus', 2.4, 1.5, 0xe0a030, xP - 1.6, yP, zP - 8, 'x');   // 100 nF
    P['PROT+'] = [xP + 1, yP + 4, zP + 9]; P['PROT-'] = [xP + 1, yP - 4, zP + 9];

    // ---- buck
    const xK = 1, yK = yb - 22;
    caixa('buck', 43, 21, 1.6, 0x1d4ea8, xK, yK, zMod + 0.8);
    for (const sx of [-1, 1]) cilindro('buck', 1.8, 6, 0xd0c08a, xK + sx * 18, yK, zT + 3);
    cilindro('buck', 6, 7, 0x2b2b2b, xK + 6, yK + 1, zMod + 1.6 + 3.5);
    cilindro('buck', 4, 9, 0x101010, xK - 6, yK + 4, zMod + 1.6 + 4.5);
    caixa('buck', 9.5, 4.5, 10, 0x2f63d8, xK - 10, yK - 7, zMod + 1.6 + 5);
    const zK = zMod + 1.6 + 1;
    P['BUCK.IN+'] = [xK - 20, yK + 3, zK]; P['BUCK.IN-'] = [xK - 20, yK - 3, zK];
    P['BUCK.OUT+'] = [xK + 20, yK + 3, zK]; P['BUCK.OUT-'] = [xK + 20, yK - 3, zK];
    for (const k of ['BUCK.IN+', 'BUCK.IN-', 'BUCK.OUT+', 'BUCK.OUT-']) cilindro('buck', 1.3, 1.2, 0xd8d8d8, P[k][0], P[k][1], zK, 'z', { metal: true });

    // ---- placa perfurada e Black Pill
    const xL = 50;
    caixa('placa', 44, 62, 1.6, 0xc9a55a, xL, yb, zMod + 0.8);
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) cilindro('placa', 1.8, 6, 0xd0c08a, xL + sx * 19, yb + sy * 28, zT + 3);
    for (const sx of [-1, 1]) caixa('placa', 2.5, 50.8, 8.5, 0x111111, xL + sx * 7.62, yb, zMod + 1.6 + 4.25);
    const zBP = zMod + 1.6 + 8.5 + 0.8;
    caixa('blackpill', 20.9, 53, 1.6, 0x16357d, xL, yb, zBP);
    caixa('blackpill', 7, 7, 1.2, 0x0b0b0b, xL, yb + 2, zBP + 1.4);
    caixa('blackpill', 9, 7.5, 3.2, 0xc4c8cc, xL, yb + 25, zBP + 2.4, { metal: true });   // USB-C (frente)
    caixa('blackpill', 3.5, 3.5, 1.4, 0xeeeeee, xL - 5, yb + 12, zBP + 1.5);              // botão KEY
    caixa('blackpill', 10.2, 2.5, 8.5, 0x111111, xL, yb - 25, zBP + 0.8 + 4.25);         // SWD (trás)
    [-3.81, -1.27, 1.27, 3.81].forEach((dx, k) => { P['SWD.' + ['3V3', 'DIO', 'CLK', 'GND'][k]] = [xL + dx, yb - 25, zBP + 0.8 + 8.5]; });
    // conectores da placa perfurada
    barraPinos('placa', 68, yb + 20, 4, 2.54); pinosEmY('J_MPU', 68, yb + 20, ['3V3', 'GND', 'SCL', 'SDA']);
    barraPinos('placa', 68, yb + 6, 4, 2.54);  pinosEmY('J_SENS', 68, yb + 6, ['3V3', 'GND', 'A', 'B']);
    barraPinos('placa', 32, yb + 24, 1, 2.54); pinosEmY('J_BP', 32, yb + 24, ['B+']);
    barraPinos('placa', 32, yb + 6, 5, 2.54);  pinosEmY('J_IBT', 32, yb + 6, ['RPWM', 'LPWM', 'EN', 'VCC', 'GND']);
    barraPinos('placa', 32, yb - 14, 2, 2.54); pinosEmY('J_BUCK', 32, yb - 14, ['5V', 'GND']);
    barraPinos('placa', 32, yb - 22, 3, 2.54); pinosEmY('J_SER', 32, yb - 22, ['GND', 'TX', 'RX']);
    // divisor (10 k e 2,2 k), 100 nF e pull-down de 10 k
    cilindro('placa', 1.1, 6.5, 0xd9c7a1, 37, yb + 20, zMod + 2.8, 'y');
    cilindro('placa', 1.1, 6.5, 0xd9c7a1, 40, yb + 15, zMod + 2.8, 'y');
    cilindro('placa', 1.8, 1.2, 0xe0a030, 43, yb + 19, zMod + 3.2, 'x');
    cilindro('placa', 1.1, 6.5, 0xd9c7a1, 37, yb - 2, zMod + 2.8, 'y');

    // ---- fonte, fusível, adaptador serial e ST-Link na mesa
    caixa('fonte', 70, 120, 34, 0xb7bdc2, -170, yb - 15, zMesa + 17, { metal: true });
    for (let k = 0; k < 6; k++) caixa('fonte', 50, 1.5, 1, 0x7d858c, -172, yb - 60 + k * 8, zMesa + 34.4);
    caixa('fonte', 6, 30, 12, 0x161616, -132, yb - 48, zMesa + 30);
    P['FONTE+'] = [-129, yb - 41, zMesa + 32]; P['FONTE-'] = [-129, yb - 52, zMesa + 32];
    cilindro('fusivel', 5.5, 34, 0x202020, -108, yb - 46, zMesa + 6, 'x');
    cilindro('fusivel', 3.2, 4, 0xbfa76a, -126, yb - 46, zMesa + 6, 'x', { metal: true });
    P['FUS.A'] = [-127, yb - 46, zMesa + 6]; P['FUS.B'] = [-90, yb - 46, zMesa + 6];
    caixa('serialusb', 16, 38, 7, 0x8a1c1c, 30, yb - 72, zMesa + 3.5);
    caixa('serialusb', 8, 8, 4, 0xc4c8cc, 30, yb - 93, zMesa + 3.5, { metal: true });
    [-2.54, 0, 2.54].forEach((dx, k) => { P['USB.' + ['GND', 'RX', 'TX'][k]] = [30 + dx, yb - 53, zMesa + 7]; });
    caixa('stlink', 18, 52, 10, 0x2b4e8c, 70, yb - 82, zMesa + 5, { metal: true });
    [-3.81, -1.27, 1.27, 3.81].forEach((dx, k) => { P['STL.' + ['3V3', 'DIO', 'CLK', 'GND'][k]] = [70 + dx, yb - 56, zMesa + 9]; });

    // ---- terminais e capacitores na tampa de trás do motor (vão com o braço)
    const yM = -C.esp_face_motor - C.motor_comp;
    for (const dz of [5, -5]) caixa('capsmotor', 3, 2.5, 4, 0xcfd3d6, -13, yM - 1.2, C.l_w + dz, { pai: gBraco, metal: true });
    cilindro('capsmotor', 2.2, 1.4, 0xe0a030, -9, yM - 3, C.l_w, 'y', { pai: gBraco });
    cilindro('capsmotor', 2.2, 1.4, 0xe0a030, -16, yM - 3, C.l_w + 11, 'y', { pai: gBraco });
    cilindro('capsmotor', 2.2, 1.4, 0xe0a030, -16, yM - 3, C.l_w - 11, 'y', { pai: gBraco });
    P['MOT+'] = [-14.5, yM - 2.4, C.l_w + 5, 1]; P['MOT-'] = [-14.5, yM - 2.4, C.l_w - 5, 1];
  }

  // ------------------------------------------------------------------------ fios
  // Ponto [x, y, z] fixo na mesa, ou [x, y, z, 1] preso ao braço (gira com a inclinação).
  // Cada fio: rede, cor, raio, nome, de, para e os pontos de controle.
  const yS = C.y_aleta;            // plano do anel dentado
  const zS = C.h_prateleira + 1.6 + 0.6;
  const SA = (dy) => [33.6, yS + dy, zS, 1];   // pinos do sensor A (+X)
  const SB = (dy) => [-33.6, yS + dy, zS, 1];  // sensor B (-X)
  const MPU = (dz) => [9.5, -C.esp_braco - 4.6 - 1.4, C.mpu_h + 7 - dz, 1];

  const FIOS = [];
  const CHICOTES = [];
  function fio(rede, cor, raio, nome, de, para, pts, extra = {}) { FIOS.push(Object.assign({ rede, cor, raio, nome, de, para, pts }, extra)); }

  function definirFios() {
    const R14 = 1.45, R22 = 0.6;
    const RED = '#c62828', BLK = '#22272b';
    // ---- chicote do motor: par trançado de 14 AWG, desce pelo lado -X do braço
    CHICOTES.push({
      rede: 'motor', raio: R14, passo: 20, afast: 1.5, chicote: 'motor',
      centro: [[-20, -74, 92, 1], [-28, -66, 76, 1], [-29, -40, 64, 1], [-26, -16, 48, 1], [-24, -15, 28, 1],
               [-25, -17, 12, 1], [-27, -26, 0, 1], [-29, -42, -8, 1], [-33, -54, -20], [-52, -66, -31],
               [-76, yb + 30, -30], [-80, yb + 17, -27]],
      fios: [
        { rede: 'motor', cor: RED, nome: 'M+ (vermelho, 14 AWG)', de: 'terminal + do motor', para: 'borne M+ do IBT-2', ini: [P['MOT+']], fim: [P['M+']] },
        { rede: 'motor', cor: BLK, nome: 'M− (preto, 14 AWG)', de: 'terminal − do motor', para: 'borne M− do IBT-2', ini: [P['MOT-']], fim: [P['M-']] },
      ],
    });
    // ---- chicote do MPU6050: 4 fios trançados, lado +X
    const jm = (n) => P['J_MPU.' + n];
    CHICOTES.push({
      rede: 'i2c', raio: R22, passo: 16, afast: 1.0, chicote: 'sinal',
      centro: [[15, -16, 55, 1], [20, -15, 44, 1], [22, -14, 30, 1], [23, -15, 16, 1], [24, -20, 4, 1], [26, -41, -6, 1],
               [29, -51, -16], [42, -62, -26], [60, -72, -28], [77, yb + 18, -20]],
      fios: [
        { rede: 'v33', cor: RED, nome: '3V3 do MPU6050', de: 'VCC do GY-521', para: 'conector do MPU na placa perfurada', ini: [MPU(0)], fim: [[72, jm('3V3')[1], zPino + 3], jm('3V3')] },
        { rede: 'gnd', cor: BLK, nome: 'GND do MPU6050', de: 'GND do GY-521', para: 'conector do MPU na placa perfurada', ini: [MPU(2.54)], fim: [[72, jm('GND')[1], zPino + 3], jm('GND')] },
        { rede: 'i2c', cor: '#2e7d32', nome: 'SCL (PB6)', de: 'SCL do GY-521', para: 'PB6 da Black Pill', ini: [MPU(5.08)], fim: [[72, jm('SCL')[1], zPino + 3], jm('SCL')] },
        { rede: 'i2c', cor: '#7cc47f', nome: 'SDA (PB7)', de: 'SDA do GY-521', para: 'PB7 da Black Pill', ini: [MPU(7.62)], fim: [[72, jm('SDA')[1], zPino + 3], jm('SDA')] },
      ],
    });
    // ---- chicote dos sensores: vem da frente, contorna o braço por baixo do suporte
    const js = (n) => P['J_SENS.' + n];
    CHICOTES.push({
      rede: 'enc', raio: R22, passo: 16, afast: 1.0, chicote: 'sinal',
      centro: [[31, 9, 18, 1], [31, -2, 14, 1], [28, -16, 9, 1], [28, -25, 0, 1], [30, -42, -8, 1],
               [33, -53, -19], [47, -64, -28], [66, -74, -29], [80, yb + 6, -21]],
      fios: [
        { rede: 'v33', cor: RED, nome: '3V3 dos sensores', de: 'VCC dos 2 sensores', para: 'conector dos sensores na placa', ini: [SA(3.8), [33, yS + 1, 21, 1]], fim: [[76, js('3V3')[1], zPino + 3], js('3V3')] },
        { rede: 'gnd', cor: BLK, nome: 'GND dos sensores', de: 'GND dos 2 sensores', para: 'conector dos sensores na placa', ini: [SA(1.27), [33.5, yS - 1, 21, 1]], fim: [[76, js('GND')[1], zPino + 3], js('GND')] },
        { rede: 'enc', cor: '#8e24aa', nome: 'Sensor A, D0 (PA15)', de: 'D0 do sensor A', para: 'PA15 da Black Pill', ini: [SA(-1.27), [34, yS - 3, 21, 1]], fim: [[76, js('A')[1], zPino + 3], js('A')] },
        { rede: 'enc', cor: '#ce93d8', nome: 'Sensor B, D0 (PB3)', de: 'D0 do sensor B', para: 'PB3 da Black Pill', ini: [SB(-1.27), [-30, yS - 4, 19, 1], [0, 8, 16.5, 1], [26, 9, 17, 1]], fim: [[76, js('B')[1], zPino + 3], js('B')] },
      ],
    });
    // 3V3 e GND do sensor B: derivados do chicote, por baixo da prateleira
    fio('v33', RED, R22, '3V3 do sensor B', 'chicote dos sensores', 'VCC do sensor B', [[31, 9.6, 18, 1], [0, 9.5, 16, 1], [-30, yS - 1, 19, 1], SB(3.8)], { chicote: 'sinal' });
    fio('gnd', BLK, R22, 'GND do sensor B', 'chicote dos sensores', 'GND do sensor B', [[31, 8.5, 17.4, 1], [0, 8.6, 15.5, 1], [-30.5, yS - 2, 19, 1], SB(1.27)], { chicote: 'sinal' });

    // ---- potência (14 AWG)
    fio('v12', RED, R14, '+12 V: fonte → fusível', 'V+ da fonte', 'fusível de 10 A', [P['FONTE+'], [-125, yb - 43, zMesa + 22], [-129, yb - 46, zMesa + 10], P['FUS.A']]);
    const N12 = [-82, yb - 40, zMesa + 10];
    fio('v12', RED, R14, '+12 V: fusível → emenda', 'fusível', 'emenda dos 2 ramos', [P['FUS.B'], [-86, yb - 44, zMesa + 7], N12]);
    fio('v12', RED, R14, '+12 V → B+ do IBT-2', 'emenda depois do fusível', 'borne B+ do IBT-2', [N12, [-80, yb - 30, zT + 4], [-77, yb - 12, zT + 12], P['B+']]);
    fio('v12', RED, R14, '+12 V → entrada do buck', 'emenda depois do fusível', 'IN+ do buck', [N12, [-74, yb - 38, zT + 8], [-38, yb - 34, zT + 13], [-23, yb - 22, zT + 13], P['BUCK.IN+']]);
    fio('gnd', BLK, R14, 'GND: fonte → B− (estrela)', 'V− da fonte', 'borne B− do IBT-2', [P['FONTE-'], [-118, yb - 50, zMesa + 16], [-96, yb - 32, zT + 2], [-80, yb - 20, zT + 11], P['B-']]);
    fio('gnd', BLK, R14, 'GND: B− → entrada do buck', 'borne B− do IBT-2', 'IN− do buck', [P['B-'], [-76, yb - 22, zT + 16], [-66, yb - 29, zT + 17], [-36, yb - 30, zT + 11], [-22, yb - 26, zT + 11], P['BUCK.IN-']]);
    fio('v12', RED, 1.0, 'Proteção → B+', 'placa de proteção', 'borne B+', [P['PROT+'], [-80, yb - 8, zT + 12], P['B+']]);
    fio('gnd', BLK, 1.0, 'Proteção → B−', 'placa de proteção', 'borne B−', [P['PROT-'], [-80, yb - 19, zT + 9], P['B-']]);
    // ---- 5 V do buck para a placa perfurada
    fio('v5', '#c2185b', 0.8, '5 V: buck → pino 5V', 'OUT+ do buck', 'pino 5V da Black Pill (placa perfurada)', [P['BUCK.OUT+'], [25, P['BUCK.OUT+'][1] + 1, zPino + 2], P['J_BUCK.5V']]);
    fio('gnd', BLK, 0.8, 'GND: buck → placa', 'OUT− do buck', 'GND da placa perfurada', [P['BUCK.OUT-'], [25, P['BUCK.OUT-'][1] + 1, zPino + 2], P['J_BUCK.GND']]);
    // ---- divisor: fio fino do B+ até a placa
    fio('vbus', '#8d6e63', 0.5, 'B+ → divisor 10 k / 2,2 k (PA4)', 'borne B+ do IBT-2', 'via B+ da placa perfurada', [P['B+'], [-74, yb - 5, zT + 22], [-62, yb + 29, zT + 25], [8, yb + 30, zT + 24], [26, yb + 26, zPino + 4], P['J_BP.B+']]);
    // ---- sinais Black Pill → IBT-2
    const ji = (n) => P['J_IBT.' + n], hi = (n) => P['IBT.' + n];
    const ponte = (a, b, h) => [a, [a[0] - 3, a[1], a[2] + h], [b[0] + 3, b[1], b[2] + h], b];
    fio('ibt', '#1565c0', R22, 'RPWM (PB0)', 'PB0', 'RPWM do IBT-2', ponte(ji('RPWM'), hi('RPWM'), 9));
    fio('ibt', '#42a5f5', R22, 'LPWM (PB1)', 'PB1', 'LPWM do IBT-2', ponte(ji('LPWM'), hi('LPWM'), 8));
    fio('ibt', '#0d47a1', R22, 'EN (PB10, R_EN e L_EN juntos)', 'PB10 (com pull-down de 10 k)', 'R_EN e L_EN do IBT-2', ponte(ji('EN'), hi('R_EN'), 7));
    fio('ibt', '#0d47a1', R22, 'jumper R_EN ↔ L_EN', 'R_EN', 'L_EN', [hi('R_EN'), [-23.2, (hi('R_EN')[1] + hi('L_EN')[1]) / 2, zPino + 2.5], hi('L_EN')]);
    fio('v33', RED, R22, 'VCC lógico do IBT-2 (3V3)', '3V3 da placa', 'VCC do IBT-2', ponte(ji('VCC'), hi('VCC'), 6));
    fio('gnd', BLK, R22, 'GND da lógica', 'GND da placa', 'GND do conector do IBT-2 (vai até o B−)', ponte(ji('GND'), hi('GND'), 5));
    // ---- serial e ST-Link (para o PC)
    const jsr = (n) => P['J_SER.' + n];
    fio('gnd', BLK, R22, 'GND do adaptador serial', 'GND da placa', 'GND do adaptador', [jsr('GND'), [28, jsr('GND')[1] - 4, zPino + 5], [29, yb - 46, zMesa + 16], P['USB.GND']]);
    fio('serial', '#ef8f00', R22, 'TX da placa (PA2) → RX do adaptador', 'PA2', 'RX do adaptador USB-serial', [jsr('TX'), [29, jsr('TX')[1] - 4, zPino + 6], [30, yb - 46, zMesa + 17], P['USB.RX']]);
    fio('serial', '#b26a00', R22, 'RX da placa (PA3) ← TX do adaptador', 'PA3', 'TX do adaptador USB-serial', [jsr('RX'), [30, jsr('RX')[1] - 4, zPino + 7], [31, yb - 46, zMesa + 18], P['USB.TX']]);
    fio('gnd', BLK, R22, 'GND do ST-Link', 'GND do SWD', 'GND do ST-Link', [P['SWD.GND'], [54, yb - 34, P['SWD.GND'][2] + 4], [72, yb - 48, zMesa + 18], P['STL.GND']]);
    fio('swd', '#c9a400', R22, 'SWDIO', 'DIO do SWD', 'SWDIO do ST-Link', [P['SWD.DIO'], [49, yb - 34, P['SWD.DIO'][2] + 5], [69, yb - 48, zMesa + 20], P['STL.DIO']]);
    fio('swd', '#7a6a00', R22, 'SWCLK', 'CLK do SWD', 'SWCLK do ST-Link', [P['SWD.CLK'], [51, yb - 34, P['SWD.CLK'][2] + 5], [71, yb - 48, zMesa + 19], P['STL.CLK']]);
  }

  // transforma um ponto de controle para o referencial da mesa
  const EIXO_Y = new THREE.Vector3(0, 1, 0);
  function mundo(p, ang) {
    const v = new THREE.Vector3(p[0], p[1], p[2]);
    if (p[3]) { v.applyAxisAngle(EIXO_Y, ang); v.z += gBraco.position.z; }
    return v;
  }
  function tubo(pontos, raio, segs) {
    const curva = new THREE.CatmullRomCurve3(pontos, false, 'centripetal');
    return new THREE.TubeGeometry(curva, segs || Math.max(16, Math.round(curva.getLength() / 1.5)), raio, 8, false);
  }
  function materialFio(cor) {
    return new THREE.MeshStandardMaterial({ color: cor, roughness: 0.45, metalness: 0.05, transparent: true, opacity: 1 });
  }

  const meshesFio = [];
  function criarFios() {
    for (const f of FIOS) {
      const m = new THREE.Mesh(new THREE.BufferGeometry(), materialFio(f.cor));
      registrar(m, { fio: f, rede: f.rede, camada: 'fios', chicote: f.chicote, movel: f.pts.some((p) => p[3]) });
      meshesFio.push(m); gFios.add(m);
    }
    for (const ch of CHICOTES) {
      ch.fios.forEach((f, k) => {
        const m = new THREE.Mesh(new THREE.BufferGeometry(), materialFio(f.cor));
        registrar(m, { fio: f, rede: f.rede, camada: 'fios', chicote: ch.chicote, movel: true, ch, k });
        meshesFio.push(m); gFios.add(m);
      });
    }
    atualizarFios(true);
  }

  function atualizarFios(tudo) {
    const ang = THREE.MathUtils.degToRad(estado.incl);
    for (const m of meshesFio) {
      const u = m.userData;
      if (!tudo && !u.movel) continue;
      let pts;
      if (u.ch) {
        const ch = u.ch, n = ch.fios.length;
        const centro = new THREE.CatmullRomCurve3(ch.centro.map((p) => mundo(p, ang)), false, 'centripetal');
        const L = centro.getLength(), N = Math.max(20, Math.round(L / 2));
        const quadros = centro.computeFrenetFrames(N, false);
        const tranca = [];
        for (let i = 1; i < N; i++) {
          const t = i / N, a = 2 * Math.PI * (t * L) / ch.passo + u.k * 2 * Math.PI / n;
          const r = ch.afast * Math.min(1, i / 4, (N - i) / 4);
          tranca.push(centro.getPointAt(t)
            .addScaledVector(quadros.normals[i], Math.cos(a) * r)
            .addScaledVector(quadros.binormals[i], Math.sin(a) * r));
        }
        pts = [...u.fio.ini.map((p) => mundo(p, ang)), ...tranca, ...u.fio.fim.map((p) => mundo(p, ang))];
      } else {
        pts = u.fio.pts.map((p) => mundo(p, ang));
      }
      m.geometry.dispose();
      m.geometry = tubo(pts, u.ch ? u.ch.raio : u.fio.raio, u.ch ? pts.length * 3 : undefined);
    }
    ultimoInclFios = estado.incl;
  }

  // ------------------------------------------------------------------- estado
  function visivelPorEtapa(o) {
    const e = estado.etapa, u = o.userData;
    const nome = u.chave;
    if (u.camada === 'fios') return e === 9;
    if (u.eletr) return nome === 'capsmotor' ? (e >= 2 && e !== 6) : e === 9;
    const g = u.peca.grupo;
    if (g === 'braco' || g === 'roda') {
      if (e === 6) return false;
      const minima = { braco: 1, rolamentos: 1, motor: 2, flange: 3, roda: 4, parafusos_m8: 4, suporte_sensores: 5, sensores: 5, mpu: 5 }[nome];
      return e >= 7 || e >= minima;
    }
    if (nome === 'barra_colares') return e >= 7;
    if (nome === 'protecao') return e >= 8;
    return e >= 6;                 // base, bandeja, almofadas
  }

  function aplicarVisibilidade() {
    for (const o of pegaveis) o.visible = visivelPorEtapa(o) && estado.camadas[o.userData.camada];
    gBarra.position.y = estado.etapa === 7 ? 110 : 0;
    gFios.visible = estado.explodir < 0.01;
  }

  function corresponde(o) {
    const u = o.userData, d = estado.destaque;
    const rede = estado.redeFixa || estado.redeFoco;
    if (rede) return u.rede === rede;
    if (!d) return true;
    if (u.chave && d.pecas.has(u.chave)) return true;
    if (u.rede && d.redes.has(u.rede)) return true;
    return !!(d.extra && d.extra(o));
  }

  function aplicarDestaque() {
    const ativo = !!(estado.destaque || estado.redeFixa || estado.redeFoco);
    for (const o of pegaveis) {
      const m = o.material, u = o.userData;
      const sel = estado.selecionado === o;
      const aceso = !ativo || corresponde(o);
      m.opacity = aceso ? u.opacidade : Math.min(u.opacidade, 0.08);
      m.depthWrite = aceso ? u.depth : false;
      m.emissive.setHex(sel && aceso ? 0x5a3c00 : 0x000000);
      for (const c of o.children) if (c.material) c.material.opacity = (!ativo || corresponde(o)) ? 0.22 : 0.03;
    }
  }

  function aplicarExplodir() {
    const k = estado.explodir;
    for (const [nome, info] of Object.entries(PECAS)) {
      const e = info.exp || [0, 0, 0];
      objPeca[nome].position.set(e[0] * k, e[1] * k, e[2] * k);
    }
    gBraco.position.z = 45 * k;
    gEletr.position.z = 35 * k;
    aplicarVisibilidade();
  }

  // ------------------------------------------------------------------ câmera
  const VISTAS = {
    iso:    { dir: [-0.62, -0.92, 0.62], alvo: [-25, -45, 15], dist: 760 },
    frente: { dir: [0.0, 1, 0.12], alvo: [0, 0, 40], dist: 640 },
    tras:   { dir: [0.05, -1, 0.35], alvo: [-20, -60, 20], dist: 700 },
    lado:   { dir: [1, 0.02, 0.12], alvo: [0, -60, 30], dist: 700 },
    cima:   { dir: [0.001, -0.25, 1], alvo: [-30, -70, 0], dist: 720 },
  };
  function irPara(alvo, posicao, ms = 650) {
    animCam = { t0: performance.now(), ms, a0: controls.target.clone(), p0: camera.position.clone(), a1: alvo, p1: posicao };
  }
  function vista(nome) {
    const v = VISTAS[nome];
    const alvo = new THREE.Vector3(...v.alvo);
    const dir = new THREE.Vector3(...v.dir).normalize();
    irPara(alvo, alvo.clone().addScaledVector(dir, v.dist));
  }
  function enquadrar(objs) {
    const caixaB = new THREE.Box3();
    for (const o of objs) if (visivelDeFato(o)) caixaB.expandByObject(o);
    if (caixaB.isEmpty()) return;
    const centro = caixaB.getCenter(new THREE.Vector3());
    const raio = caixaB.getSize(new THREE.Vector3()).length() / 2;
    const dir = camera.position.clone().sub(controls.target).normalize();
    const dist = Math.max(160, raio / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.95);
    irPara(centro, centro.clone().addScaledVector(dir, dist));
  }

  // ------------------------------------------------------------- interação
  function objetoSob(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    ponteiro.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ponteiro, camera);
    const vis = pegaveis.filter((o) => o.material.opacity > 0.15 && visivelDeFato(o));
    const hit = raycaster.intersectObjects(vis, false)[0];
    return hit ? hit.object : null;
  }
  function visivelDeFato(o) {
    for (let p = o; p; p = p.parent) if (!p.visible) return false;
    return true;
  }
  function nomeDe(o) {
    const u = o.userData;
    if (u.fio) return u.fio.nome;
    if (u.peca) return u.peca.nome;
    return u.eletr.nome;
  }
  function descrever(o) {
    const u = o.userData;
    const linhas = [];
    if (u.fio) {
      const f = u.fio;
      linhas.push(['Rede', REDES[f.rede].nome]);
      linhas.push(['De', f.de]);
      linhas.push(['Para', f.para]);
      linhas.push(['Bitola', (u.ch ? u.ch.raio : f.raio) >= 1.2 ? '14 AWG (potência)' : '22 a 24 AWG (sinal)']);
      if (u.chicote) linhas.push(['Chicote', u.chicote === 'motor' ? 'motor: lado −X do braço' : 'sinais: lado +X do braço']);
      return { nome: f.nome, linhas, tarefas: tarefasDaRede(f.rede), rede: f.rede };
    }
    if (u.peca) {
      const p = u.peca;
      linhas.push(['Tipo', p.tipo === 'impressa' ? 'impressa (PETG)' : 'comprada']);
      if (p.massa) linhas.push(['Massa prevista', p.massa.massa_g.toFixed(0) + ' g (CAD)']);
      if (p.massa && p.massa.dimensoes_mm) linhas.push(['Dimensões', p.massa.dimensoes_mm.map((x) => x.toFixed(0)).join(' × ') + ' mm']);
      return { nome: p.nome, linhas, tarefas: p.tarefas };
    }
    return { nome: u.eletr.nome, linhas, tarefas: u.eletr.tarefas };
  }
  function tarefasDaRede(rede) {
    return Object.entries(TAREFA_3D).filter(([id, t]) => (t.redes || []).includes(rede) && t.redes.length < 6).map(([id]) => id);
  }

  function aoMover(ev) {
    const dica = document.getElementById('dica');
    const o = objetoSob(ev);
    renderer.domElement.style.cursor = o ? 'pointer' : '';
    if (!o) { dica.style.display = 'none'; return; }
    const r = renderer.domElement.getBoundingClientRect();
    dica.textContent = nomeDe(o);
    dica.style.left = (ev.clientX - r.left) + 'px';
    dica.style.top = (ev.clientY - r.top) + 'px';
    dica.style.display = 'block';
  }
  let baixo = null;
  function aoClicar(ev) {
    if (!baixo || Math.hypot(ev.clientX - baixo[0], ev.clientY - baixo[1]) > 4) return;
    const o = objetoSob(ev);
    estado.selecionado = o;
    aplicarDestaque();
    aoSelecionar(o ? descrever(o) : null);
  }

  // ------------------------------------------------------------------- laço
  function redimensionar() {
    const el = document.getElementById('cena');
    const w = el.clientWidth, h = el.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  let tAnt = performance.now();
  function quadro(t) {
    requestAnimationFrame(quadro);
    const dt = Math.min(0.05, (t - tAnt) / 1000); tAnt = t;
    if (estado.girar) definir({ giro: (estado.giro + dt * 90) % 360 }, true);
    if (estado.balancar) definir({ incl: C.angulo_batente * Math.sin(t / 1000 * 1.4) }, true);
    if (animCam) {
      const k = Math.min(1, (t - animCam.t0) / animCam.ms), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      controls.target.lerpVectors(animCam.a0, animCam.a1, e);
      camera.position.lerpVectors(animCam.p0, animCam.p1, e);
      if (k >= 1) animCam = null;
    }
    controls.update();
    if (document.getElementById('aba-3d').classList.contains('ativa')) renderer.render(scene, camera);
  }

  // ---------------------------------------------------------------- API
  let aoMudarEstado = () => {};
  function definir(mud, deAnimacao) {
    Object.assign(estado, mud);
    if ('incl' in mud) {
      gBraco.rotation.y = THREE.MathUtils.degToRad(estado.incl);
      if (gFios.visible && estado.etapa === 9 && Math.abs(estado.incl - ultimoInclFios) > 0.05) atualizarFios(false);
    }
    if ('giro' in mud) gRodaPivo.rotation.y = THREE.MathUtils.degToRad(estado.giro);
    if ('explodir' in mud) { aplicarExplodir(); if (estado.explodir < 0.01) atualizarFios(true); }
    if ('etapa' in mud || 'camadas' in mud) { aplicarVisibilidade(); if (estado.etapa === 9) atualizarFios(true); }
    if ('destaque' in mud || 'redeFoco' in mud || 'redeFixa' in mud) aplicarDestaque();
    aoMudarEstado(estado, deAnimacao);
  }

  function init() {
    const el = document.getElementById('cena');
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputEncoding = THREE.sRGBEncoding;
    el.appendChild(renderer.domElement);
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(32, 1, 5, 6000);
    camera.up.set(0, 0, 1);
    camera.position.set(-400, -600, 400);
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.12;
    controls.target.set(-25, -45, 15);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x7d8894, 0.75);
    hemi.position.set(0, 0, 1);
    scene.add(hemi);
    const sol = new THREE.DirectionalLight(0xffffff, 0.75);
    sol.position.set(-250, -320, 520);
    scene.add(sol);
    const contra = new THREE.DirectionalLight(0xffffff, 0.35);
    contra.position.set(300, 380, 200);
    scene.add(contra);

    const grade = new THREE.GridHelper(900, 45, 0x9aa6b2, 0xc6ced6);
    grade.rotation.x = Math.PI / 2;
    grade.position.set(-50, -60, zMesa - 0.3);
    scene.add(grade);

    gEst = new THREE.Group(); gBarra = new THREE.Group(); gBraco = new THREE.Group();
    gRodaPivo = new THREE.Group(); gEletr = new THREE.Group(); gFios = new THREE.Group();
    gRodaPivo.position.set(0, 0, C.l_w);
    const gRoda = new THREE.Group(); gRoda.position.set(0, 0, -C.l_w); gRodaPivo.add(gRoda);
    gBraco.add(gRodaPivo);
    gEst.add(gBarra);
    scene.add(gEst, gBraco, gEletr, gFios);

    criarPecas();
    criarEletronica();
    definirFios();
    criarFios();

    raycaster = new THREE.Raycaster();
    ponteiro = new THREE.Vector2();
    renderer.domElement.addEventListener('pointermove', aoMover);
    renderer.domElement.addEventListener('pointerleave', () => { document.getElementById('dica').style.display = 'none'; });
    renderer.domElement.addEventListener('pointerdown', (ev) => { baixo = [ev.clientX, ev.clientY]; });
    renderer.domElement.addEventListener('pointerup', aoClicar);
    new ResizeObserver(redimensionar).observe(el);
    redimensionar();
    aplicarVisibilidade();
    const v = VISTAS.iso, d = new THREE.Vector3(...v.dir).normalize();
    controls.target.set(...v.alvo);
    camera.position.copy(controls.target).addScaledVector(d, v.dist);
    requestAnimationFrame(quadro);
  }

  function destacarTarefa(id) {
    const t = TAREFA_3D[id];
    if (!t) return;
    const destaque = (t.pecas.length || (t.redes || []).length || t.extra)
      ? { pecas: new Set(t.pecas), redes: new Set(t.redes || []), extra: t.extra } : null;
    definir({ etapa: t.etapa, destaque, redeFixa: null, redeFoco: null, selecionado: null, explodir: 0 });
    const alvo = destaque ? pegaveis.filter((o) => o.visible && corresponde(o)) : pegaveis.filter((o) => o.visible);
    enquadrar(alvo.length ? alvo : pegaveis);
  }

  return {
    init, definir, vista, destacarTarefa, estado, enquadrar: () => enquadrar(pegaveis),
    set aoSelecionar(f) { aoSelecionar = f; },
    set aoMudarEstado(f) { aoMudarEstado = f; },
  };
})();
