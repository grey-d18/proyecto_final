// Piezas que usan varias pantallas: íconos, voz, memoria del reciclador, menú y mapas.

// --- Seguridad: todo texto que viene de la base de datos pasa por esc() antes de mostrarse,
// para que nadie pueda «inyectar» código escribiendo, por ejemplo, <script> en su nombre.
export function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export const soles = (n) => (n == null ? "—" : `S/ ${Number(n).toFixed(2)}`);

// --- Íconos (líneas simples, toman el color del texto) ----------------------------------------
const trazos = {
  reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  micro: '<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M19 11a7 7 0 0 1-14 0"/><path d="M12 18v3"/>',
  parlante: '<path d="M11 5 6 9H3v6h3l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
  atras: '<path d="m15 6-6 6 6 6"/>',
  adelante: '<path d="m9 6 6 6-6 6"/>',
  carrito: '<path d="M3 4h2l2.4 11h10.2L20 7H6.2"/><circle cx="9" cy="19" r="1.6"/><circle cx="17" cy="19" r="1.6"/>',
  casa: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  tienda: '<path d="M4 9h16l-1.5-5h-13z"/><path d="M5 9v11h14V9"/><path d="M9 20v-5h6v5"/>',
  mapa: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14"/><path d="M15 6v14"/>',
  camion: '<path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="1.8"/><circle cx="17" cy="18" r="1.8"/>',
  libro: '<path d="M4 5h6a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H4z"/><path d="M20 5h-6a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h6z"/>',
  documento: '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4"/><path d="M9 13h6"/><path d="M9 17h6"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alerta: '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  descargar: '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
  ubicacion: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  lapiz: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  grafico: '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
};

export function icono(nombre, tamano = 24, grosor = 2) {
  return `<svg width="${tamano}" height="${tamano}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${grosor}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${trazos[nombre]}</svg>`;
}

export const logo = `<span class="logo" style="color:#FFFFFF">${icono("micro", 22)}</span>`;

// --- Voz: reproduce las preguntas y avisos grabados (carpeta audios/) ------------------------------
let audioActual = null;
export function hablar(clave) {
  callar();
  audioActual = new Audio(`audios/${clave}.mp3`);
  // El navegador puede bloquear el sonido hasta que la persona toque algo: no es un error.
  audioActual.play().catch(() => {});
  return audioActual;
}
let turno = 0; // sube cada vez que algo nuevo empieza a sonar: así una lectura vieja no sigue
export function callar() {
  turno += 1;
  if (audioActual) { audioActual.pause(); audioActual = null; }
  try { speechSynthesis.cancel(); } catch { /* el navegador no tiene voz */ }
}

// Lee un texto que cambia (por ejemplo, el resumen de la ficha) con la voz del propio celular.
// No usamos un servicio de voz en internet: el texto tiene datos personales (DNI, celular)
// y así no sale del teléfono.
export function leerEnVoz(texto) {
  callar();
  try {
    const frase = new SpeechSynthesisUtterance(texto);
    const voces = speechSynthesis.getVoices();
    frase.voice = voces.find((v) => v.lang === "es-PE") || voces.find((v) => v.lang.startsWith("es")) || null;
    frase.lang = frase.voice?.lang || "es-PE";
    frase.rate = 0.9;
    speechSynthesis.speak(frase);
  } catch { /* sin voz: la ficha igual se puede leer en pantalla */ }
}

// El resumen de la ficha en tres partes: Camila (audio grabado) dice la frase fija de
// inicio, la voz del celular lee los datos personales y Camila dice la frase fija del final.
export function leerFichaEnVoz(claveInicio, datos, claveFinal) {
  callar(); // corta lo que estuviera sonando
  const mio = turno;
  const sigue = (paso) => () => { if (turno === mio) paso(); };
  const camila = (clave, despues) => {
    audioActual = new Audio(`audios/${clave}.mp3`);
    audioActual.addEventListener("ended", sigue(despues));
    audioActual.addEventListener("error", sigue(despues)); // si falta el audio, sigue con lo demás
    audioActual.play().catch(() => {});
  };
  const celular = (texto, despues) => {
    try {
      const frase = new SpeechSynthesisUtterance(texto);
      const voces = speechSynthesis.getVoices();
      frase.voice = voces.find((v) => v.lang === "es-PE") || voces.find((v) => v.lang.startsWith("es")) || null;
      frase.lang = frase.voice?.lang || "es-PE";
      frase.rate = 0.9;
      frase.addEventListener("end", sigue(despues));
      speechSynthesis.speak(frase);
    } catch { despues(); }
  };
  camila(claveInicio, () => celular(datos, () => camila(claveFinal, () => {})));
}

// --- Memoria: qué reciclador está usando la app (queda guardado en este celular) -------------------
const CLAVE = "ecobarrio.reciclador";
export const sesion = {
  get codigo() { try { return localStorage.getItem(CLAVE); } catch { return null; } },
  set codigo(valor) {
    try { valor ? localStorage.setItem(CLAVE, valor) : localStorage.removeItem(CLAVE); } catch { /* modo privado */ }
  },
};

// --- Barra de arriba con «Volver» -----------------------------------------------------------------
export function barra(volverA, titulo = "") {
  return `<div class="barra">
    <a class="boton-redondo" href="${volverA}" aria-label="Volver">${icono("atras", 22)}</a>
    <span style="font-weight:700;color:var(--suave)">${titulo}</span>
    <span style="width:48px"></span>
  </div>`;
}

// --- Menú de abajo del reciclador -----------------------------------------------------------------
export function menuReciclador(activa, pendientes = 0) {
  const opcion = (ruta, nombre, ico, extra = "") =>
    `<a href="#/${ruta}" ${activa === ruta ? 'aria-current="page"' : ""}><span class="icono">${icono(ico, 26, 1.8)}${extra}</span>${nombre}</a>`;
  const globo = pendientes ? `<span class="globo" aria-label="${pendientes} pendientes">${pendientes}</span>` : "";
  return `<nav class="menu-abajo" aria-label="Menú del reciclador"><div class="dentro">
    ${opcion("reciclador", "Inicio", "casa")}
    ${opcion("mi-ruta", "Mi ruta", "mapa")}
    ${opcion("recoger", "Recoger", "camion", globo)}
    ${opcion("aprender", "Aprender", "libro")}
  </div></nav>`;
}

export const cargando = (texto = "Cargando…") =>
  `<div class="zona-micro"><div class="girando" role="status" aria-label="${texto}"></div><p class="subtitulo">${texto}</p></div>`;

export const mensajeError = (error) => `<div class="error" role="alert">${esc(error.message || error)}</div>`;

// --- Mapas (Leaflet + OpenStreetMap) ------------------------------------------------------------
export function nuevoMapa(elemento, centro, zoom = 14) {
  const mapa = L.map(elemento, { scrollWheelZoom: false }).setView(centro, zoom);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(mapa);
  return mapa;
}

export function pin(tipo, texto = "") {
  return L.divIcon({ className: "", html: `<div class="pin ${tipo}">${texto}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] });
}
