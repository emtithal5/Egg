// Deterministic Three.js scene for the power-feed explainer.
// window.renderAt(t) draws the frame at time t (seconds); the renderer script steps through it.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const W = 1920, H = 1080;
export const DURATION = 68;

// ---------------------------------------------------------------- colours
const C_BLUE = new THREE.Color('#3d9bff');
const C_GREEN = new THREE.Color('#2fd67a');
const C_GREY = new THREE.Color('#59606a');

// ---------------------------------------------------------------- timeline
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const smooth = (a, b, t) => { const x = clamp01((t - a) / (b - a)); return x * x * (3 - 2 * x); };
// 1 = mains available. Outage at 24.5 s, mains back for the side-by-side replay at 43.8 s, outage again at 52 s.
const lampOn = (t) => (t < 24.5 || (t >= 43.8 && t < 52)) ? 1 : 0;
const mainsFlow = (t) => 1 - smooth(24.6, 25.3, t) + smooth(43.9, 44.5, t) - smooth(52.1, 52.8, t);
// 1 = DC bus fed from rectifiers (batteries floating / charging), 0 = batteries supply the bus.
const busFromMains = (t) => 1 - smooth(25.0, 25.6, t) + smooth(44.2, 44.8, t) - smooth(52.5, 53.1, t);

// phase that only advances while a path is active, so mains pulses freeze when the source drops
function integrate(fn, t) {
  const dt = 1 / 60; let acc = 0;
  for (let s = 0; s < t; s += dt) acc += fn(s) * Math.min(dt, t - s);
  return acc;
}

// ---------------------------------------------------------------- renderer
const canvas = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#14181d');
scene.fog = new THREE.Fog('#14181d', 22, 40);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(34, W / H, 0.1, 100);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.7, 0.35, 0.9);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ---------------------------------------------------------------- lights
scene.add(new THREE.HemisphereLight('#c9d6e6', '#20242a', 0.55));
const key = new THREE.DirectionalLight('#fff4e6', 1.6);
key.position.set(-6, 9, 8);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left: -10, right: 10, top: 6, bottom: -3, near: 1, far: 30 });
key.shadow.bias = -0.0004;
key.shadow.normalBias = 0.02;
scene.add(key);
const fill = new THREE.DirectionalLight('#9fc2ff', 0.45);
fill.position.set(8, 4, 6);
scene.add(fill);

// ---------------------------------------------------------------- materials
const std = (color, roughness = 0.5, metalness = 0.2, extra = {}) =>
  new THREE.MeshStandardMaterial({ color, roughness, metalness, ...extra });
const M = {
  ral7035: std('#aeb3b7', 0.6, 0.15),
  cabinet: std('#2c3138', 0.5, 0.35),
  cabinetInner: std('#1d2126', 0.6, 0.3),
  black: std('#121417', 0.55, 0.3),
  steel: std('#8d939a', 0.35, 0.85),
  galv: std('#a7adb3', 0.4, 0.8),
  copper: std('#c07a45', 0.28, 0.9, { emissive: new THREE.Color(0, 0, 0) }),
  cable: std('#0d0e10', 0.65, 0.1),
  battery: std('#3a4047', 0.6, 0.05),
  batteryLid: std('#4a5159', 0.55, 0.05),
  red: std('#b3261e', 0.5, 0.1),
  plastic: std('#23272c', 0.6, 0.1),
  floor: std('#2a2f35', 0.75, 0.05),
  wall: std('#323840', 0.9, 0.0),
};

function box(w, h, d, mat, x, y, z, parent = scene, shadow = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = shadow; m.receiveShadow = true;
  parent.add(m);
  return m;
}
function cyl(r, h, mat, x, y, z, rotX = 0, parent = scene, seg = 24) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), mat);
  m.position.set(x, y, z); m.rotation.x = rotX;
  m.castShadow = true; parent.add(m);
  return m;
}
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
function plane(w, h, map, x, y, z, parent = scene, emissive = false) {
  const mat = emissive
    ? new THREE.MeshBasicMaterial({ map, toneMapped: false })
    : new THREE.MeshStandardMaterial({ map, roughness: 0.6, metalness: 0.2 });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  m.position.set(x, y, z); m.receiveShadow = true;
  parent.add(m);
  return m;
}
const ledMat = (color) => new THREE.MeshBasicMaterial({ color, toneMapped: false });

// ---------------------------------------------------------------- room
{
  const tiles = canvasTex(1024, 1024, (g, w, h) => {
    g.fillStyle = '#2b3036'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 4000; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * 0.025})`; g.fillRect(Math.random() * w, Math.random() * h, 2, 2); }
    g.strokeStyle = '#1b1f23'; g.lineWidth = 4;
    for (let i = 0; i <= 4; i++) { g.beginPath(); g.moveTo(i * w / 4, 0); g.lineTo(i * w / 4, h); g.stroke(); g.beginPath(); g.moveTo(0, i * h / 4); g.lineTo(w, i * h / 4); g.stroke(); }
  });
  tiles.wrapS = tiles.wrapT = THREE.RepeatWrapping; tiles.repeat.set(15, 7.5);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 30), new THREE.MeshStandardMaterial({ map: tiles, roughness: 0.55, metalness: 0.1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.z = 8; floor.receiveShadow = true;
  scene.add(floor);

  const wallTex = canvasTex(1024, 512, (g, w, h) => {
    g.fillStyle = '#30363d'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#262b31'; g.lineWidth = 3;
    for (let i = 0; i <= 8; i++) { g.beginPath(); g.moveTo(i * w / 8, 0); g.lineTo(i * w / 8, h); g.stroke(); }
    g.fillStyle = '#2a2f35'; g.fillRect(0, h * 0.86, w, h * 0.14);
  });
  wallTex.wrapS = THREE.RepeatWrapping; wallTex.repeat.set(5, 1);
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(60, 9), new THREE.MeshStandardMaterial({ map: wallTex, roughness: 0.9 }));
  wall.position.set(0, 4.5, -2.0); wall.receiveShadow = true;
  scene.add(wall);
  // soft station "pads" on the floor to separate the three stations visually
  for (const [x, w] of [[-5.6, 2.3], [0.2, 3.9], [5.38, 2.2]]) {
    const pad = new THREE.Mesh(new THREE.PlaneGeometry(w, 2.1), std('#353b42', 0.7, 0.05));
    pad.rotation.x = -Math.PI / 2; pad.position.set(x, 0.002, -0.85); pad.receiveShadow = true;
    scene.add(pad);
  }
}

// ---------------------------------------------------------------- cable ladder (overhead)
const TRAY_Y = 2.6;
{
  const x0 = -6.3, x1 = 6.3;
  box(x1 - x0, 0.06, 0.02, M.galv, (x0 + x1) / 2, TRAY_Y, -1.2);
  box(x1 - x0, 0.06, 0.02, M.galv, (x0 + x1) / 2, TRAY_Y, -0.8);
  for (let x = x0 + 0.1; x < x1; x += 0.3) box(0.03, 0.015, 0.4, M.galv, x, TRAY_Y - 0.02, -1.0);
  for (let x = x0 + 0.3; x < x1; x += 2.1) {
    cyl(0.008, 2, M.steel, x, TRAY_Y + 1.0, -1.22);
    cyl(0.008, 2, M.steel, x, TRAY_Y + 1.0, -0.78);
    box(0.04, 0.03, 0.5, M.steel, x, TRAY_Y - 0.05, -1.0);
  }
}

// ---------------------------------------------------------------- station 1: mains distribution panel
const S1 = { x: -5.6, z: -1.0 };
const acPanel = {};
{
  const g = new THREE.Group(); g.position.set(S1.x, 0, S1.z); scene.add(g);
  const w = 1.3, h = 2.0, d = 0.5, fz = d / 2;
  box(w, 0.1, d - 0.04, M.black, 0, 0.05, 0, g);
  box(w, h - 0.1, d, M.ral7035, 0, 0.05 + (h - 0.1) / 2, 0, g);
  // two doors: seams + hinges + handles
  box(0.008, h - 0.16, 0.01, M.cabinetInner, 0, h / 2 + 0.03, fz + 0.003, g, false);
  for (const sx of [-1, 1]) {
    box(0.03, 0.16, 0.03, M.black, sx * 0.1, 1.0, fz + 0.02, g);
    for (const hy of [0.4, 1.7]) box(0.02, 0.08, 0.02, M.steel, sx * (w / 2 - 0.02), hy, fz + 0.005, g);
  }
  // instrument plate (left door): voltmeter + availability lamp
  const plate = canvasTex(512, 256, (c, W2, H2) => {
    c.fillStyle = '#20252b'; c.fillRect(0, 0, W2, H2);
    c.strokeStyle = '#59626c'; c.lineWidth = 6; c.strokeRect(3, 3, W2 - 6, H2 - 6);
  });
  plane(0.5, 0.25, plate, -0.33, 1.62, fz + 0.004, g);
  const dial = canvasTex(256, 256, (c) => {
    c.fillStyle = '#f2f2ee'; c.beginPath(); c.arc(128, 128, 124, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#222'; c.lineWidth = 4;
    for (let i = 0; i <= 10; i++) {
      const a = Math.PI * (1.25 - i * 0.05);
      c.beginPath(); c.moveTo(128 + Math.cos(a) * 100, 128 - Math.sin(a) * 100);
      c.lineTo(128 + Math.cos(a) * (i % 5 ? 88 : 78), 128 - Math.sin(a) * (i % 5 ? 88 : 78)); c.stroke();
    }
    c.fillStyle = '#c62828'; c.fillRect(158, 50, 30, 6);
  });
  const face = new THREE.Mesh(new THREE.CircleGeometry(0.075, 40), new THREE.MeshStandardMaterial({ map: dial, roughness: 0.3 }));
  face.position.set(-0.43, 1.62, fz + 0.012); g.add(face);
  cyl(0.082, 0.02, M.black, -0.43, 1.62, fz + 0.004, Math.PI / 2, g);
  const needle = new THREE.Mesh(new THREE.BoxGeometry(0.004, 0.065, 0.002), new THREE.MeshBasicMaterial({ color: '#111' }));
  needle.geometry.translate(0, 0.0325, 0);
  needle.position.set(-0.43, 1.6, fz + 0.016); g.add(needle);
  acPanel.needle = needle;
  // pilot lamp
  cyl(0.034, 0.03, M.steel, -0.22, 1.62, fz + 0.012, Math.PI / 2, g);
  const lens = new THREE.Mesh(new THREE.SphereGeometry(0.026, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshBasicMaterial({ color: '#3d9bff', toneMapped: false }));
  lens.rotation.x = Math.PI / 2; lens.position.set(-0.22, 1.62, fz + 0.026); g.add(lens);
  acPanel.lens = lens;
  const lampLight = new THREE.PointLight('#5aa8ff', 0.0, 0.8, 2); lampLight.position.set(-0.22, 1.62, fz + 0.12); g.add(lampLight);
  acPanel.lampLight = lampLight;
  // warning label + louvres
  const warn = canvasTex(128, 128, (c) => {
    c.fillStyle = '#f5c400'; c.beginPath(); c.moveTo(64, 8); c.lineTo(122, 116); c.lineTo(6, 116); c.closePath(); c.fill();
    c.strokeStyle = '#111'; c.lineWidth = 8; c.stroke();
    c.fillStyle = '#111'; c.beginPath(); c.moveTo(70, 34); c.lineTo(46, 78); c.lineTo(64, 78); c.lineTo(56, 104); c.lineTo(84, 64); c.lineTo(66, 64); c.closePath(); c.fill();
  });
  const wm = plane(0.12, 0.12, warn, 0.33, 1.6, fz + 0.004, g); wm.material.transparent = true;
  for (let i = 0; i < 6; i++) for (const sx of [-1, 1]) box(0.36, 0.012, 0.012, M.cabinetInner, sx * 0.33, 0.3 + i * 0.035, fz + 0.004, g, false);
  // cable gland on top
  cyl(0.05, 0.05, M.black, 0, h + 0.02, -0.05, 0, g);
}

// ---------------------------------------------------------------- station 2: DC power unit + battery rack
const S2 = { x: -0.9, z: -1.0 };
const FZ = -0.65;           // front plane of the power cabinet (world z)
const OZ = -0.6;            // flow-overlay plane, just in front of the cabinet face
const pu = {};
{
  const g = new THREE.Group(); scene.add(g);
  const w = 0.9, h = 2.2, d = 0.7, x = S2.x, z = S2.z;
  box(w, 0.08, d - 0.04, M.black, x, 0.04, z, g);
  // carcass: sides, top, back, inner panel (front open behind clear covers)
  box(0.04, h - 0.08, d, M.cabinet, x - w / 2 + 0.02, 0.08 + (h - 0.08) / 2, z, g);
  box(0.04, h - 0.08, d, M.cabinet, x + w / 2 - 0.02, 0.08 + (h - 0.08) / 2, z, g);
  box(w, 0.05, d, M.cabinet, x, h - 0.025, z, g);
  box(w - 0.08, h - 0.13, 0.03, M.cabinetInner, x, 0.08 + (h - 0.13) / 2, z - d / 2 + 0.015, g);
  box(w - 0.08, h - 0.13, 0.02, M.cabinetInner, x, 0.08 + (h - 0.13) / 2, FZ - 0.08, g);
  // front frame rails
  box(0.03, h - 0.08, 0.02, M.cabinet, x - w / 2 + 0.055, 0.08 + (h - 0.08) / 2, FZ - 0.01, g);
  box(0.03, h - 0.08, 0.02, M.cabinet, x + w / 2 - 0.055, 0.08 + (h - 0.08) / 2, FZ - 0.01, g);

  // controller with status screen (icons only, no assumed values)
  box(0.45, 0.16, 0.06, M.plastic, -0.975, 2.06, FZ - 0.03, g);
  const screen = (mainsOK) => canvasTex(256, 96, (c, W2, H2) => {
    c.fillStyle = '#071018'; c.fillRect(0, 0, W2, H2);
    // AC symbol
    c.lineWidth = 6; c.strokeStyle = mainsOK ? '#3d9bff' : '#4d5560';
    c.beginPath(); for (let i = 0; i <= 40; i++) { const px = 24 + i * 1.6, py = 48 - Math.sin(i / 40 * Math.PI * 2) * 16; i ? c.lineTo(px, py) : c.moveTo(px, py); } c.stroke();
    if (!mainsOK) { c.strokeStyle = '#e0533d'; c.lineWidth = 5; c.beginPath(); c.moveTo(22, 74); c.lineTo(92, 22); c.stroke(); }
    // battery symbol + direction arrow
    const col = mainsOK ? '#3d9bff' : '#2fd67a';
    c.strokeStyle = '#c8d0d8'; c.lineWidth = 5; c.strokeRect(150, 30, 70, 38); c.fillStyle = '#c8d0d8'; c.fillRect(220, 40, 8, 18);
    c.fillStyle = col; c.fillRect(156, 36, mainsOK ? 58 : 44, 26);
    c.fillStyle = col; c.beginPath();
    if (mainsOK) { c.moveTo(122, 49); c.lineTo(138, 40); c.lineTo(138, 58); } else { c.moveTo(140, 49); c.lineTo(124, 40); c.lineTo(124, 58); }
    c.closePath(); c.fill();
  });
  pu.screenOn = screen(true); pu.screenOff = screen(false);
  pu.screen = plane(0.36, 0.135, pu.screenOn, -0.975, 2.06, FZ + 0.002, g, true);
  box(0.02, 0.02, 0.01, M.steel, -0.79, 2.03, FZ + 0.002, g);

  // DC output distribution: row of breakers
  box(0.62, 0.3, 0.05, M.plastic, -0.9, 1.76, FZ - 0.035, g);
  for (let i = 0; i < 9; i++) {
    box(0.05, 0.13, 0.05, std('#9ea4aa', 0.55, 0.05), -1.16 + i * 0.065, 1.77, FZ - 0.015, g);
    box(0.016, 0.03, 0.02, M.black, -1.16 + i * 0.065, 1.79, FZ + 0.012, g);
  }

  // common DC bus bar behind a clear cover
  box(0.8, 0.05, 0.025, M.copper, -0.86, 1.52, FZ - 0.025, g);
  pu.bus = g.children[g.children.length - 1];
  const cover = new THREE.Mesh(new THREE.BoxGeometry(0.84, 0.12, 0.005), new THREE.MeshStandardMaterial({ color: '#cfe3ff', transparent: true, opacity: 0.12, roughness: 0.05 }));
  cover.position.set(-0.86, 1.52, FZ + 0.005); g.add(cover);

  // rectifier shelf with three plug-in modules
  box(0.76, 0.54, 0.05, M.plastic, -0.9, 1.16, FZ - 0.04, g);
  const grille = canvasTex(128, 256, (c, W2, H2) => {
    c.fillStyle = '#c9cdd1'; c.fillRect(0, 0, W2, H2);
    c.fillStyle = '#2a2e33';
    for (let yy = 70; yy < 230; yy += 12) for (let xx = 14; xx < 116; xx += 12) { c.beginPath(); c.arc(xx, yy, 4, 0, Math.PI * 2); c.fill(); }
    c.fillStyle = '#9aa1a8'; c.fillRect(10, 14, 108, 36);
  });
  pu.rectLeds = [];
  for (const mx of [-1.13, -0.9, -0.67]) {
    box(0.21, 0.48, 0.05, std('#c9cdd1', 0.45, 0.3), mx, 1.16, FZ - 0.02, g);
    plane(0.2, 0.46, grille, mx, 1.16, FZ + 0.006, g);
    const led = new THREE.Mesh(new THREE.CircleGeometry(0.009, 16), ledMat('#38e07b'));
    led.position.set(mx - 0.06, 1.37, FZ + 0.008); g.add(led); pu.rectLeds.push(led);
    const led2 = new THREE.Mesh(new THREE.CircleGeometry(0.009, 16), ledMat('#222'));
    led2.position.set(mx - 0.03, 1.37, FZ + 0.008); g.add(led2);
    box(0.12, 0.02, 0.03, M.steel, mx, 0.96, FZ + 0.012, g);
  }
  // lower blanking + vents
  box(0.76, 0.6, 0.02, M.plastic, -0.9, 0.5, FZ - 0.05, g);
  for (let i = 0; i < 10; i++) box(0.6, 0.012, 0.012, M.black, -0.9, 0.3 + i * 0.04, FZ - 0.035, g, false);
  // cable entries on top
  for (const ex of [-1.3, -0.58]) cyl(0.04, 0.04, M.black, ex, h + 0.01, ex < -1 ? -1.05 : -0.95, 0, g);
  // side entry gland (battery cable)
  const sg = cyl(0.035, 0.03, M.black, -0.44, 1.52, -0.95, 0, g); sg.rotation.z = Math.PI / 2;
}

// battery rack: generic two-tier rack; block count/arrangement is illustrative only
const batt = {};
{
  const g = new THREE.Group(); scene.add(g);
  const x0 = 0.3, x1 = 1.9, z = -1.0, d = 0.6;
  for (const px of [x0, x1]) for (const pz of [z - d / 2, z + d / 2]) box(0.04, 1.2, 0.04, M.steel, px, 0.6, pz, g);
  for (const sy of [0.12, 0.66]) {
    box(x1 - x0, 0.03, 0.04, M.steel, (x0 + x1) / 2, sy, z - d / 2, g);
    box(x1 - x0, 0.03, 0.04, M.steel, (x0 + x1) / 2, sy, z + d / 2, g);
    box(x1 - x0 - 0.04, 0.01, d, M.galv, (x0 + x1) / 2, sy + 0.015, z, g);
  }
  box(x1 - x0, 0.03, 0.04, M.steel, (x0 + x1) / 2, 1.2, z - d / 2, g);
  box(x1 - x0, 0.03, 0.04, M.steel, (x0 + x1) / 2, 1.2, z + d / 2, g);
  const bw = 0.34, bh = 0.4, bd = 0.46;
  batt.blocks = [];
  for (const sy of [0.13, 0.67]) {
    for (let i = 0; i < 4; i++) {
      const bx = x0 + 0.2 + i * 0.4;
      const b = box(bw, bh, bd, M.battery, bx, sy + 0.02 + bh / 2, z, g);
      box(bw + 0.004, 0.04, bd + 0.004, M.batteryLid, bx, sy + 0.02 + bh - 0.02, z, g);
      cyl(0.022, 0.03, M.red, bx - 0.1, sy + 0.02 + bh + 0.015, z + 0.12, 0, g, 16);
      cyl(0.022, 0.03, M.black, bx + 0.1, sy + 0.02 + bh + 0.015, z + 0.12, 0, g, 16);
      batt.blocks.push(b);
    }
  }
  // highlight frame (glow intensity driven by state)
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(x1 - x0 + 0.12, 1.32, d + 0.12)),
    new THREE.LineBasicMaterial({ color: C_GREEN, transparent: true, opacity: 0, toneMapped: false }));
  edges.position.set((x0 + x1) / 2, 0.62, z); g.add(edges);
  batt.edges = edges;
  const glow = new THREE.PointLight('#2fd67a', 0, 3.2, 1.6); glow.position.set(1.1, 1.0, -0.2); g.add(glow);
  batt.light = glow;
}

// ---------------------------------------------------------------- station 3: telecom racks
const S3 = { xs: [5.0, 5.75], z: -1.0 };
const leds = [];   // { mesh, kind: 'pwr'|'act'|'stat', seed }
{
  const U = 0.0445;
  const face = (kind) => canvasTex(512, 128, (c, W2, H2) => {
    const bg = { tx: '#2b3440', sw: '#23272c', pp: '#1c1f23', rt: '#303740', bl: '#15171a' }[kind];
    c.fillStyle = bg; c.fillRect(0, 0, W2, H2);
    c.fillStyle = 'rgba(255,255,255,.06)'; c.fillRect(0, 0, W2, 6);
    if (kind === 'sw' || kind === 'pp') {
      for (let i = 0; i < 24; i++) { const px = 120 + i * 15 + Math.floor(i / 6) * 6; c.fillStyle = '#0a0b0c'; c.fillRect(px, kind === 'sw' ? 40 : 46, 11, 34); c.fillStyle = '#6b737c'; c.fillRect(px, kind === 'sw' ? 40 : 46, 11, 3); }
    }
    if (kind === 'tx' || kind === 'rt') {
      for (let i = 0; i < 6; i++) { c.fillStyle = '#11151a'; c.beginPath(); c.arc(330 + i * 28, 64, 9, 0, Math.PI * 2); c.fill(); c.strokeStyle = '#8e969f'; c.lineWidth = 3; c.stroke(); }
      c.fillStyle = '#0b0e12'; c.fillRect(110, 34, 150, 60);
      c.strokeStyle = '#46505b'; c.lineWidth = 2; c.strokeRect(110, 34, 150, 60);
      for (let i = 0; i < 6; i++) { c.fillStyle = 'rgba(0,0,0,.4)'; c.fillRect(20, 24 + i * 14, 70, 6); }
    }
    if (kind === 'bl') for (let i = 0; i < 30; i++) { c.fillStyle = '#0c0d0f'; c.fillRect(20 + i * 16, 50, 8, 28); }
    c.fillStyle = '#9aa1a8'; c.fillRect(4, 10, 8, H2 - 20); c.fillRect(W2 - 12, 10, 8, H2 - 20);
  });
  const tex = { tx: face('tx'), sw: face('sw'), pp: face('pp'), rt: face('rt'), bl: face('bl') };
  const layouts = [
    [['pp', 1], ['sw', 1], ['bl', 1], ['tx', 3], ['tx', 3], ['bl', 1], ['rt', 2], ['tx', 4], ['bl', 1], ['tx', 3], ['sw', 1], ['bl', 1], ['tx', 4], ['tx', 3], ['bl', 1], ['rt', 2], ['pp', 1], ['bl', 2]],
    [['pp', 1], ['sw', 1], ['sw', 1], ['bl', 1], ['rt', 2], ['tx', 4], ['tx', 3], ['bl', 1], ['tx', 3], ['bl', 1], ['rt', 2], ['tx', 4], ['bl', 1], ['tx', 3], ['sw', 1], ['pp', 1], ['bl', 3]],
  ];
  let seed = 1;
  S3.xs.forEach((x, ri) => {
    const g = new THREE.Group(); scene.add(g);
    const w = 0.7, h = 2.2, d = 1.0, z = S3.z, fz = z + d / 2;
    box(w, 0.06, d, M.black, x, 0.03, z, g);
    box(w, 0.05, d, M.black, x, h - 0.025, z, g);
    for (const sx of [-1, 1]) box(0.03, h, d, M.black, x + sx * (w / 2 - 0.015), h / 2, z, g);
    box(w - 0.06, h - 0.1, 0.02, M.cabinetInner, x, h / 2, z - d / 2 + 0.01, g);
    for (const sx of [-1, 1]) box(0.025, h - 0.12, 0.02, M.steel, x + sx * 0.245, h / 2, fz - 0.06, g);
    // equipment from the top down
    let yTop = h - 0.12;
    for (const [kind, nU] of layouts[ri]) {
      const hh = nU * U - 0.003;
      const yc = yTop - hh / 2;
      box(0.48, hh, kind === 'bl' ? 0.02 : 0.55, std('#1b1e22', 0.5, 0.35), x, yc, fz - 0.06 - (kind === 'bl' ? 0.01 : 0.275), g);
      plane(0.48, hh, tex[kind], x, yc, fz - 0.05 + 0.001, g);
      if (kind !== 'bl' && kind !== 'pp') {
        const pwr = new THREE.Mesh(new THREE.CircleGeometry(0.0055, 12), ledMat('#38e07b'));
        pwr.position.set(x - 0.205, yc + Math.min(0.012, hh / 4), fz - 0.048); g.add(pwr);
        leds.push({ mesh: pwr, kind: 'pwr' });
        const n = kind === 'sw' ? 8 : 4;
        for (let i = 0; i < n; i++) {
          const a = new THREE.Mesh(new THREE.CircleGeometry(0.0045, 10), ledMat('#38e07b'));
          a.position.set(x - 0.16 + i * (kind === 'sw' ? 0.042 : 0.02), yc - (kind === 'sw' ? 0.012 : Math.min(0.03, hh / 3)), fz - 0.048);
          g.add(a);
          leds.push({ mesh: a, kind: i === 0 && kind !== 'sw' ? 'stat' : 'act', seed: seed++, amber: (seed % 5 === 0) });
        }
      }
      yTop -= nU * U;
    }
    // cable entry on top
    cyl(0.045, 0.04, M.black, x, h + 0.01, -0.95, 0, g);
  });
}

// ---------------------------------------------------------------- cables & flow overlays
function roundedPath(pts, r) {
  const v = pts.map((p) => new THREE.Vector3(...p));
  const path = new THREE.CurvePath();
  let cur = v[0].clone();
  for (let i = 1; i < v.length; i++) {
    const p = v[i];
    if (i < v.length - 1) {
      const a = p.clone().sub(v[i - 1]), b = v[i + 1].clone().sub(p);
      const rr = Math.min(r, a.length() / 2, b.length() / 2);
      const e = p.clone().sub(a.normalize().multiplyScalar(rr));
      const s = p.clone().add(b.normalize().multiplyScalar(rr));
      if (cur.distanceTo(e) > 1e-4) path.add(new THREE.LineCurve3(cur, e));
      path.add(new THREE.QuadraticBezierCurve3(e, p.clone(), s));
      cur = s;
    } else path.add(new THREE.LineCurve3(cur, p));
  }
  return path;
}

const flowVS = /* glsl */`
  varying float vU; varying vec3 vN; varying vec3 vV;
  void main() {
    vU = uv.x;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }`;
const flowFS = /* glsl */`
  uniform vec3 uColor; uniform vec3 uGrey; uniform float uActive; uniform float uPhase; uniform float uLen;
  uniform float uSpacing; uniform float uDir; uniform float uReveal; uniform float uGain; uniform float uIdle;
  varying float vU; varying vec3 vN; varying vec3 vV;
  void main() {
    float s = vU * uLen;
    float rim = pow(1.0 - abs(dot(vN, vV)), 1.6);
    float core = 0.35 + 0.65 * (1.0 - rim);
    float ph = fract((s * uDir - uPhase) / uSpacing);
    float head = smoothstep(0.45, 0.96, ph) * (1.0 - smoothstep(0.96, 1.0, ph));
    float on = uActive * step(s, uReveal * uLen + 0.0001);
    vec3 col = uColor * (0.32 + 2.6 * head) * uGain * on;
    vec3 idle = uGrey * uIdle * (1.0 - on);
    gl_FragColor = vec4((col + idle) * core, 1.0);
  }`;

const flows = {};
const arrowGeo = new THREE.ConeGeometry(1, 2.4, 3);
arrowGeo.rotateX(Math.PI / 2); // tip along +z
function addFlow(id, pts, { cable = 0, glowR = 0.05, spacing = 0.8, speed = 1.0, corner = 0.12, arrows = true, idle = 0.22, cableUntil = pts.length } = {}) {
  const path = roundedPath(pts, corner);
  const len = path.getLength();
  if (cable) {
    const cpath = roundedPath(pts.slice(0, cableUntil), corner);
    const m = new THREE.Mesh(new THREE.TubeGeometry(cpath, Math.max(16, Math.ceil(cpath.getLength() * 40)), cable, 12, false), M.cable);
    m.castShadow = true; scene.add(m);
  }
  const uni = {
    uColor: { value: C_BLUE.clone() }, uGrey: { value: C_GREY.clone() }, uActive: { value: 0 }, uPhase: { value: 0 },
    uLen: { value: len }, uSpacing: { value: spacing }, uDir: { value: 1 }, uReveal: { value: 1 }, uGain: { value: 1 }, uIdle: { value: idle },
  };
  const mat = new THREE.ShaderMaterial({ uniforms: uni, vertexShader: flowVS, fragmentShader: flowFS, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
  const tube = new THREE.Mesh(new THREE.TubeGeometry(path, Math.max(24, Math.ceil(len * 60)), glowR, 14, false), mat);
  scene.add(tube);
  const arr = [];
  if (arrows) {
    const n = Math.max(1, Math.floor(len / spacing));
    for (let i = 0; i < n; i++) {
      const a = new THREE.Mesh(arrowGeo, new THREE.MeshBasicMaterial({ color: C_BLUE, transparent: true, opacity: 0, toneMapped: false, depthWrite: false }));
      a.scale.setScalar(glowR * 0.95);
      scene.add(a); arr.push(a);
    }
  }
  flows[id] = { path, len, uni, arr, spacing, speed };
  return flows[id];
}

const zA = -1.05, zD = -0.95, YT = TRAY_Y + 0.045;
// mains: panel -> tray -> power unit top -> rectifier shelf
addFlow('acExt', [[S1.x, 2.0, zA], [S1.x, YT, zA], [-1.3, YT, zA], [-1.3, 2.2, zA]], { cable: 0.03, glowR: 0.055, spacing: 0.9, speed: 1.1 });
addFlow('acInt', [[-1.3, 2.2, zA], [-1.3, 2.2, OZ], [-1.3, 1.2, OZ], [-1.24, 1.2, OZ]], { glowR: 0.018, spacing: 0.3, speed: 0.37, corner: 0.04 });
// rectifier outputs onto the common DC bus
['r1', 'r2', 'r3'].forEach((id, i) => addFlow(id, [[[-1.13, -0.9, -0.67][i], 1.42, OZ], [[-1.13, -0.9, -0.67][i], 1.505, OZ]], { glowR: 0.014, spacing: 0.1, speed: 0.12, arrows: false }));
// DC bus -> output distribution -> top -> tray -> transmitter racks
addFlow('loadInt', [[-0.9, 1.53, OZ], [-0.9, 1.76, OZ], [-0.58, 1.76, OZ], [-0.58, 2.2, OZ], [-0.58, 2.2, zD]], { glowR: 0.018, spacing: 0.3, speed: 0.37, corner: 0.04 });
addFlow('loadExt', [[-0.58, 2.2, zD], [-0.58, YT, zD], [S3.xs[0], YT, zD], [S3.xs[0], 2.2, zD]], { cable: 0.032, glowR: 0.055, spacing: 0.9, speed: 1.1 });
addFlow('loadB', [[S3.xs[0], YT, zD], [S3.xs[1], YT, zD], [S3.xs[1], 2.2, zD]], { cable: 0.03, glowR: 0.05, spacing: 0.9, speed: 1.1 });
// battery string <-> common DC bus (defined from the battery towards the bus)
const batPts = [[0.5, 1.13, zD], [0.5, 1.52, zD], [-0.44, 1.52, zD], [-0.47, 1.52, OZ], [-0.5, 1.52, OZ]];
addFlow('batDis', batPts, { cable: 0.03, cableUntil: 3, glowR: 0.05, spacing: 0.6, speed: 0.75, idle: 0 });
addFlow('batChg', batPts, { glowR: 0.05, spacing: 0.6, speed: 0.35, idle: 0.22 });
flows.batChg.uni.uDir.value = -1;

// ---------------------------------------------------------------- per-frame state
const tmpQ = new THREE.Quaternion(), zAxis = new THREE.Vector3(0, 0, 1);
function setFlow(f, { color, active, phase, reveal = 1, gain = 1, dir }) {
  f.uni.uColor.value.copy(color);
  f.uni.uActive.value = active;
  f.uni.uPhase.value = phase * f.speed;
  f.uni.uReveal.value = reveal;
  f.uni.uGain.value = gain;
  if (dir !== undefined) f.uni.uDir.value = dir;
  const d = f.uni.uDir.value;
  f.arr.forEach((a, i) => {
    // arrow sits on each pulse head
    let s = (i * f.spacing + phase * f.speed) % f.len;
    if (d < 0) s = f.len - s;
    s = ((s % f.len) + f.len) % f.len;
    const u = s / f.len;
    const vis = active * (s <= reveal * f.len ? 1 : 0) * smooth(0.0, 0.08, u) * (1 - smooth(0.93, 1.0, u));
    a.material.opacity = vis; a.material.color.copy(color);
    a.visible = vis > 0.01;
    a.position.copy(f.path.getPointAt(u));
    const tan = f.path.getTangentAt(u).multiplyScalar(d);
    a.quaternion.copy(tmpQ.setFromUnitVectors(zAxis, tan));
  });
}

const reveal = (t, a, b) => smooth(a, b, t);
const camKeys = [
  { t: 0, p: [-0.9, 3.0, 14.4], q: [0, 1.45, -1] },
  { t: 5, p: [-0.3, 2.6, 12.6], q: [0, 1.4, -1] },
  { t: 9, p: [-1.2, 2.5, 12.3], q: [-0.35, 1.4, -1] },
  { t: 24, p: [0.9, 2.5, 12.3], q: [0.3, 1.4, -1] },
  { t: 27, p: [1.0, 2.45, 12.2], q: [0.3, 1.4, -1] },
  { t: 42, p: [-0.4, 2.45, 12.4], q: [-0.05, 1.4, -1] },
  { t: 44.5, p: [-0.05, 2.5, 12.5], q: [-0.05, 1.4, -1] },
  { t: 999, p: [-0.05, 2.5, 12.5], q: [-0.05, 1.4, -1] },
];
function cameraAt(t) {
  let i = 0; while (camKeys[i + 1].t < t) i++;
  const a = camKeys[i], b = camKeys[i + 1];
  const k = smooth(a.t, b.t, t);
  const lerp = (u, v) => u.map((x, j) => x + (v[j] - x) * k);
  camera.position.set(...lerp(a.p, b.p));
  camera.lookAt(new THREE.Vector3(...lerp(a.q, b.q)));
  camera.updateMatrixWorld();
}

// ---------------------------------------------------------------- HUD
const $ = (id) => document.getElementById(id);
const hud = {
  title: $('title'), cap1: $('cap1'), cap2: $('cap2'), badge: $('badge'), legend: $('legend'), fade: $('fade'),
  st1: $('st1'), st2: $('st2'), st3: $('st3'),
  tags: { tagRect: [-1.25, 1.16, OZ, -150, 0], tagBus: [-1.25, 1.52, OZ, -230, -70], tagDist: [-1.2, 1.76, OZ, -170, -120], tagBatt: [1.1, 1.22, -0.7, 120, -70] },
  leaders: $('leaders'),
};
const proj = (x, y, z) => { const v = new THREE.Vector3(x, y, z).project(camera); return [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H]; };
const opa = (el, o) => { el.style.opacity = o.toFixed(3); el.style.visibility = o < 0.005 ? 'hidden' : 'visible'; };
const win = (t, a, b, f = 0.6) => smooth(a, a + f, t) * (1 - smooth(b - f, b, t));

function updateHud(t, mains, fromMains) {
  opa(hud.title, win(t, 0.4, 5.2, 0.8));
  opa(hud.cap1, win(t, 10.5, 24.4, 0.6) + win(t, 44.6, 51.9, 0.5));
  opa(hud.cap2, win(t, 26.2, 42.6, 0.6) + win(t, 53.2, 68.5, 0.5));
  const badgeO = win(t, 9.5, 68.5, 0.6);
  opa(hud.badge, badgeO);
  const st1 = t < 25 || (t >= 44 && t < 52.5);
  hud.badge.querySelector('span').textContent = st1 ? 'الحالة الأولى: الكهرباء العمومية متوفرة' : 'الحالة الثانية: انقطاع الكهرباء العمومية';
  hud.badge.querySelector('i').style.background = st1 ? 'var(--blue)' : 'var(--green)';
  opa(hud.legend, win(t, 9.0, 68.5, 0.8));

  const stO = win(t, 3.8, 68.5, 0.8);
  [[hud.st1, S1.x, 0, -0.1], [hud.st2, 0.2, 0, -0.1], [hud.st3, 5.38, 0, -0.1]].forEach(([el, x, y, z]) => {
    const [px, py] = proj(x, y, z); el.style.left = px + 'px'; el.style.top = (py + 14) + 'px'; opa(el, stO);
  });
  const chip1 = hud.st1.querySelector('.chip');
  chip1.textContent = mains ? 'المصدر: متوفر' : 'المصدر: منقطع';
  chip1.style.color = mains ? '#7fbfff' : '#ff8a7a'; chip1.style.borderColor = mains ? '#3d9bff' : '#e0533d';
  const chip3 = hud.st3.querySelector('.chip');
  chip3.textContent = 'قيد التشغيل'; chip3.style.color = '#7ff0b0'; chip3.style.borderColor = '#2fd67a';

  let svg = '';
  const tagO = win(t, 9.6, 68.5, 0.8);
  for (const [id, [x, y, z, dx, dy]] of Object.entries(hud.tags)) {
    const el = $(id); const [px, py] = proj(x, y, z);
    let o = tagO;
    if (id === 'tagBatt') {
      el.style.borderColor = fromMains > 0.5 ? 'rgba(61,155,255,.6)' : 'rgba(47,214,122,.9)';
    }
    el.style.left = (px + dx) + 'px'; el.style.top = (py + dy) + 'px'; opa(el, o);
    if (o > 0.01) svg += `<line x1="${px}" y1="${py}" x2="${px + dx * 0.72}" y2="${py + dy}" stroke="rgba(230,236,242,${0.55 * o})" stroke-width="2"/><circle cx="${px}" cy="${py}" r="4" fill="rgba(230,236,242,${0.85 * o})"/>`;
  }
  hud.leaders.innerHTML = svg;
  hud.fade.style.opacity = (1 - smooth(0, 0.8, t) + smooth(67.2, 68, t)).toFixed(3);
}

// ---------------------------------------------------------------- render
function renderAt(t) {
  cameraAt(t);
  const lamp = lampOn(t), mf = mainsFlow(t), fm = busFromMains(t);
  const mainsPhase = integrate(mainsFlow, t);
  const loadCol = C_GREEN.clone().lerp(C_BLUE, fm);

  // initial explanatory reveal of the feed sequence: panel -> rectifiers -> output -> transmitters
  setFlow(flows.acExt, { color: C_BLUE, active: mf, phase: mainsPhase, reveal: reveal(t, 5.6, 7.4) });
  setFlow(flows.acInt, { color: C_BLUE, active: mf, phase: mainsPhase, reveal: reveal(t, 7.4, 7.9) });
  ['r1', 'r2', 'r3'].forEach((id) => setFlow(flows[id], { color: C_BLUE, active: mf, phase: mainsPhase, reveal: reveal(t, 7.9, 8.1) }));
  setFlow(flows.loadInt, { color: loadCol, active: 1, phase: t, reveal: reveal(t, 8.2, 8.7) });
  setFlow(flows.loadExt, { color: loadCol, active: 1, phase: t, reveal: reveal(t, 8.7, 10.2) });
  setFlow(flows.loadB, { color: loadCol, active: 1, phase: t, reveal: reveal(t, 10.2, 10.6) });
  // batteries: float/charge from the bus while mains is present (subdued), supply the bus when it is not
  setFlow(flows.batChg, { color: C_BLUE, active: fm * reveal(t, 10.6, 10.7), phase: t, gain: 0.55, reveal: reveal(t, 10.6, 11.4) });
  setFlow(flows.batDis, { color: C_GREEN, active: 1 - fm, phase: t, gain: 1.15 });

  // DC bus glow follows whichever source is supporting it
  const busO = reveal(t, 8.0, 8.4);
  M.copper.emissive.copy(loadCol).multiplyScalar(0.55 * busO);

  // station 1 indicators
  acPanel.lens.material.color.set(lamp ? '#3d9bff' : '#1b2129');
  acPanel.lampLight.intensity = lamp ? 0.08 : 0;
  acPanel.needle.rotation.z = THREE.MathUtils.lerp(1.0, -0.35, mf);
  // power unit indicators
  pu.screen.material.map = lamp ? pu.screenOn : pu.screenOff;
  pu.rectLeds.forEach((l) => l.material.color.set(mf > 0.5 ? '#38e07b' : '#1e2328'));

  // battery highlight during outage
  const bh = 1 - fm;
  batt.edges.material.opacity = 0.85 * bh;
  batt.light.intensity = 1.4 * bh;
  batt.blocks.forEach((b) => { b.material.emissive?.setRGB(0.0, 0.025 * bh, 0.012 * bh); });

  // transmitter LEDs: power/status steady in both states, traffic LEDs flicker
  for (const l of leds) {
    if (l.kind === 'act') {
      const k = Math.floor(t * 9 + l.seed * 3.7);
      const hsh = Math.sin(k * 12.9898 + l.seed * 78.233) * 43758.5453;
      const on = (hsh - Math.floor(hsh)) > 0.35;
      l.mesh.material.color.set(on ? (l.amber ? '#ffb02e' : '#38e07b') : '#16301f');
    }
  }

  updateHud(t, lamp, fm);
  composer.render();
}

window.renderAt = renderAt;
window.DURATION = DURATION;
document.fonts.ready.then(() => { renderAt(0); window.ready = true; });
