// La app es UNA sola página: según lo que diga la dirección después de «#», se dibuja una
// pantalla u otra (por ejemplo, …/index.html#/mi-ruta). Así funciona en GitHub Pages, que
// solo sirve archivos, y los botones «atrás» del celular siguen funcionando.
import { callar, mensajeError } from "./comun.js";
import { API } from "./config.js";

const pantallas = {
  "": () => import("./vistas/inicio.js"),
  reciclador: () => import("./vistas/reciclador.js"),
  registro: () => import("./vistas/registro.js"),
  "mi-ruta": () => import("./vistas/mi_ruta.js"),
  recoger: () => import("./vistas/recoger.js"),
  aprender: () => import("./vistas/aprender.js"),
  vecino: () => import("./vistas/vecino.js"),
  acopiador: () => import("./vistas/acopiador.js"),
  municipalidad: () => import("./vistas/municipalidad.js"),
};

const raiz = document.getElementById("app");
let limpiarAnterior = null;

async function mostrar() {
  const ruta = location.hash.replace(/^#\/?/, "").split("?")[0];
  const cargar = pantallas[ruta] ?? pantallas[""];
  callar();                             // si sonaba un audio de otra pantalla, se calla
  if (limpiarAnterior) limpiarAnterior(); // cada pantalla puede apagar lo suyo (micrófono, mapa…)
  limpiarAnterior = null;
  window.scrollTo(0, 0);
  try {
    const pantalla = await cargar();
    limpiarAnterior = (await pantalla.mostrar(raiz)) || null;
  } catch (error) {
    console.error(error);
    raiz.innerHTML = `<div class="pantalla">${mensajeError(error)}<a class="boton" href="#/">Volver al inicio</a></div>`;
  }
}

// Versión de prueba: si no llegó la dirección del servidor (la laptop de la autora), se avisa.
function servidorApagado() {
  raiz.innerHTML = `
    <div class="pantalla">
      <header><span class="subtitulo">Recicla Contigo · versión de prueba</span><h1>El servidor está apagado</h1></header>
      <p>Esta demo funciona mientras la autora tiene encendido el servidor en su laptop. Para usarla, abra el
      enlace o el código QR que ella comparte al empezar la presentación.</p>
      <p class="nota">Por qué: la parte que entiende la voz (Whisper) necesita una computadora con más memoria de la
      que dan los servicios gratuitos. En producción correría en un servidor pagado (unos US$ 10 al mes).</p>
    </div>`;
}

if (API) {
  window.addEventListener("hashchange", mostrar);
  mostrar();
} else {
  servidorApagado();
}
