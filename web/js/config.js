// Dónde está la API (la carpeta api/ del proyecto).
//
// Esta es una versión de PRUEBA: la API corre en la laptop de la autora y se conecta a
// internet con un túnel temporal de Cloudflare (ver scripts/demo_en_vivo.sh). Cada vez
// que se enciende, el túnel tiene una dirección nueva, que llega en el enlace:
//     https://grey-d18.github.io/proyecto_final/?api=https://algo.trycloudflare.com
// La página la recuerda en este navegador. En producción, aquí iría la dirección fija de
// un servidor pagado (ver README, «Costos»).
const enMiLaptop = ["localhost", "127.0.0.1"].includes(location.hostname);

// Solo se aceptan túneles de Cloudflare (o la laptop): así nadie puede mandar un enlace
// que haga que la app envíe los datos (DNI, voz) a otro servidor.
function direccionValida(texto) {
  try {
    const url = new URL(texto);
    const tunel = url.protocol === "https:" && url.hostname.endsWith(".trycloudflare.com");
    const local = url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname);
    return tunel || local ? url.origin : null;
  } catch {
    return null;
  }
}

function leerGuardada() {
  try { return localStorage.getItem("reciclacontigo-api"); } catch { return null; }
}

function guardar(direccion) {
  try { localStorage.setItem("reciclacontigo-api", direccion); } catch { /* modo privado: no pasa nada */ }
}

const parametros = new URLSearchParams(location.search);
const deEnlace = direccionValida(parametros.get("api") || "");
if (parametros.has("api")) {
  // Se quita «?api=…» de la barra para que la dirección se vea limpia.
  history.replaceState(null, "", location.pathname + location.hash);
}
if (deEnlace) guardar(deEnlace);

export const API =
  deEnlace ||
  (enMiLaptop ? `http://${location.hostname}:8000` : null) ||
  direccionValida(leerGuardada() || "");
