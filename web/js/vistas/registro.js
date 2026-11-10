// Registro por voz: el flujo principal del producto.
//   Paso 0      bienvenida y consentimiento (al apretar «Empezar» se abre el micrófono).
//   Pasos 1–8   una pregunta por pantalla: se escucha sola; la persona toca el micrófono y habla.
//   Paso 9      la IA llena la ficha; la persona la revisa y se inscribe.
//   Final       código de registro y constancia en PDF.
import { enlace, enviar, enviarFormulario, leer } from "../api.js";
import { barra, callar, cargando, esc, hablar, icono, mensajeError, sesion } from "../comun.js";
import { abrirMicrofono, cerrarMicrofono, grabar, microfonoAbierto } from "../grabadora.js";

let catalogo = null;
// Lo que se va respondiendo. Vive mientras la página esté abierta (si vuelve atrás, no se pierde).
const estado = { paso: 0, respuestas: {}, ficha: null, metodo: "", codigo: null };
let grabacion = null;

export async function mostrar(raiz) {
  if (estado.codigo) Object.assign(estado, { paso: 0, respuestas: {}, ficha: null, metodo: "", codigo: null });
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  catalogo ??= await leer("/catalogos");
  dibujar(raiz);
  return () => { grabacion?.detener(); cerrarMicrofono(); };
}

function dibujar(raiz) {
  const total = catalogo.preguntas.length;
  if (estado.codigo) return dibujarFinal(raiz);
  if (estado.paso === 0) return dibujarBienvenida(raiz);
  if (estado.paso <= total) return dibujarPregunta(raiz);
  return dibujarFicha(raiz);
}

const irA = (raiz, paso) => { callar(); grabacion?.detener(); estado.paso = paso; window.scrollTo(0, 0); dibujar(raiz); };

// --- Paso 0 ------------------------------------------------------------------------------
function dibujarBienvenida(raiz) {
  raiz.innerHTML = `
  <div class="pantalla">
    ${barra(sesion.codigo ? "#/reciclador" : "#/")}
    <h1>Registro de recicladores</h1>
    <div class="tarjeta">
      <button class="boton chico suave" type="button" id="escuchar" style="align-self:flex-start">${icono("parlante", 20)} Escuchar</button>
      <p>Le haremos <strong>${catalogo.preguntas.length} preguntas</strong>. Escuche cada una y responda hablando.</p>
      <p class="subtitulo">Sus datos solo se usan para el Registro Municipal de Recicladores (Ley 29419).</p>
    </div>
    <label class="casilla"><input type="checkbox" id="acepto"> Acepto registrarme y que se usen mis datos para el registro.</label>
    <div id="aviso-micro"></div>
    <div class="empuja"></div>
    <button class="boton principal ancho" type="button" id="empezar" disabled>Empezar</button>
  </div>`;
  const empezar = raiz.querySelector("#empezar");
  raiz.querySelector("#acepto").addEventListener("change", (e) => { empezar.disabled = !e.target.checked; });
  raiz.querySelector("#escuchar").addEventListener("click", () => hablar("bienvenida_registro"));
  empezar.addEventListener("click", async () => {
    try {
      await abrirMicrofono(); // el navegador pide permiso aquí, una sola vez
    } catch {
      // Sin micrófono igual se puede seguir: las respuestas se escriben.
      raiz.querySelector("#aviso-micro").innerHTML =
        `<div class="aviso">${icono("alerta", 22)}<span>No pudimos usar el micrófono. Puede escribir las respuestas, o dar permiso al micrófono en el navegador.</span></div>`;
      await new Promise((r) => setTimeout(r, 1800));
    }
    irA(raiz, 1);
  });
}

// --- Pasos 1 a 8 -----------------------------------------------------------------------------
function dibujarPregunta(raiz) {
  const total = catalogo.preguntas.length;
  const pregunta = catalogo.preguntas[estado.paso - 1];
  const clave = pregunta.clave;
  const ultima = estado.paso === total;

  raiz.innerHTML = `
  <div class="pantalla">
    <div style="display:flex;flex-direction:column;gap:12px">
      ${barra("#/registro", `Pregunta ${estado.paso} de ${total}`).replace('href="#/registro"', 'href="#/registro" id="volver"')}
      <div class="progreso" style="--total:${total}" aria-hidden="true">
        ${catalogo.preguntas.map((_, i) => `<span class="${i < estado.paso ? "hecho" : ""}"></span>`).join("")}
      </div>
    </div>
    <section class="tarjeta pregunta">
      <button class="boton chico suave" type="button" id="escuchar" style="align-self:flex-start">${icono("parlante", 20)} Escuchar otra vez</button>
      <h1>${esc(pregunta.texto)}</h1>
      <p class="subtitulo">Por ejemplo: «${esc(pregunta.ejemplo)}»</p>
    </section>
    <div class="zona-micro" id="zona"></div>
    <div class="par">
      <button class="boton" type="button" id="anterior">Anterior</button>
      <button class="boton principal" type="button" id="siguiente">${ultima ? "Terminar" : "Siguiente"}</button>
    </div>
  </div>`;

  const zona = raiz.querySelector("#zona");
  let escribiendo = false;

  const dibujarZona = (modo, mensaje = "") => {
    const respuesta = estado.respuestas[clave] || "";
    if (escribiendo) {
      zona.innerHTML = `
        <label class="campo" style="width:100%;text-align:left"><span>Escriba su respuesta</span>
          <textarea id="escrito">${esc(respuesta)}</textarea></label>
        <button class="boton chico" type="button" id="hablar">${icono("micro", 20)} Mejor la digo</button>`;
      zona.querySelector("#escrito").addEventListener("input", (e) => { estado.respuestas[clave] = e.target.value; });
      zona.querySelector("#escrito").focus();
      zona.querySelector("#hablar").addEventListener("click", () => { escribiendo = false; dibujarZona("esperando"); });
      return;
    }
    if (modo === "grabando") {
      zona.innerHTML = `
        <button class="micro grabando" type="button" id="micro" aria-label="Terminar de hablar" style="color:#FFFFFF">
          <svg width="52" height="52" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button>
        <div class="onda" aria-hidden="true">${"<span></span>".repeat(9)}</div>
        <span class="etiqueta" style="font-size:20px;font-weight:700">Le escuchamos… Cuando termine, se detiene solo</span>`;
    } else if (modo === "escuchando") {
      zona.innerHTML = `<div class="girando" role="status" aria-label="Entendiendo su respuesta"></div><p class="subtitulo">Entendiendo su respuesta…</p>`;
    } else if (respuesta) {
      zona.innerHTML = `
        <div class="entendimos">
          <span class="nota" style="font-weight:700">Entendimos:</span>
          <span class="texto">${esc(respuesta)}</span>
          <div class="chips">
            <button class="boton chico" type="button" id="otra-vez">${icono("micro", 20)} Decirlo otra vez</button>
            <button class="boton chico" type="button" id="escribir">${icono("lapiz", 20)} Corregir escribiendo</button>
          </div>
        </div>`;
    } else {
      zona.innerHTML = `
        ${mensaje ? `<div class="aviso">${icono("alerta", 22)}<span>${mensaje}</span></div>` : ""}
        <button class="micro" type="button" id="micro" aria-label="Tocar para hablar" style="color:#FFFFFF">${icono("micro", 64, 1.8)}</button>
        <span style="font-size:20px;font-weight:700">Toque para hablar</span>
        <button class="enlace" type="button" id="escribir">Prefiero escribir</button>`;
    }
    zona.querySelector("#micro")?.addEventListener("click", tocarMicro);
    zona.querySelector("#otra-vez")?.addEventListener("click", () => { delete estado.respuestas[clave]; tocarMicro(); });
    zona.querySelector("#escribir")?.addEventListener("click", () => { escribiendo = true; dibujarZona(); });
  };

  async function tocarMicro() {
    if (grabacion) return grabacion.detener(); // segundo toque: terminar
    callar();
    if (!microfonoAbierto()) {
      try { await abrirMicrofono(); } catch {
        return dibujarZona("esperando", "No pudimos usar el micrófono. Puede escribir su respuesta.");
      }
    }
    dibujarZona("grabando");
    const barras = [...zona.querySelectorAll(".onda span")];
    grabacion = grabar((v) => barras.forEach((b, i) => {
      b.style.height = `${Math.min(36, 8 + v * 400 * (0.5 + ((i * 7) % 5) / 5))}px`;
    }));
    const { audio, extension } = await grabacion.terminado;
    grabacion = null;
    if (!document.body.contains(zona)) return; // la persona salió de la pantalla
    dibujarZona("escuchando");
    try {
      const formulario = new FormData();
      formulario.append("audio", audio, `respuesta${extension}`);
      const { texto } = await enviarFormulario("/transcribir", formulario);
      if (texto.trim()) {
        estado.respuestas[clave] = texto.trim();
        dibujarZona();
      } else {
        dibujarZona("esperando", "No escuchamos nada. Toque el micrófono y hable cerca del celular.");
      }
    } catch (error) {
      dibujarZona("esperando", esc(error.message));
    }
  }

  dibujarZona();
  hablar(clave); // la pregunta se escucha sola
  raiz.querySelector("#escuchar").addEventListener("click", () => hablar(clave));
  raiz.querySelector("#anterior").addEventListener("click", () => irA(raiz, estado.paso - 1));
  raiz.querySelector("#volver").addEventListener("click", (e) => { e.preventDefault(); irA(raiz, estado.paso - 1); });
  raiz.querySelector("#siguiente").addEventListener("click", () => {
    if (ultima) estado.ficha = null; // al terminar, la ficha se vuelve a llenar con las respuestas actuales
    irA(raiz, estado.paso + 1);
  });
}

// --- Paso 9: revisar la ficha -----------------------------------------------------------------
const NOMBRES_CAMPO = {
  nombre_completo: "nombre", dni: "DNI", edad: "edad", distrito_vivienda: "distrito",
  sector_vivienda: "barrio", materiales: "materiales", medio_transporte: "con qué recoge",
  pertenece_asociacion: "asociación", nombre_asociacion: "asociación", equipo_proteccion: "protección",
};

async function dibujarFicha(raiz) {
  if (!estado.ficha) {
    raiz.innerHTML = `<div class="pantalla">${cargando("Ordenando sus respuestas en la ficha…")}</div>`;
    try {
      const { ficha, metodo } = await enviar("/ficha", { respuestas: estado.respuestas });
      estado.ficha = ficha;
      estado.metodo = metodo;
    } catch (error) {
      raiz.innerHTML = `<div class="pantalla">${mensajeError(error)}<button class="boton" id="reintentar">Intentar otra vez</button></div>`;
      raiz.querySelector("#reintentar").addEventListener("click", () => dibujarFicha(raiz));
      return;
    }
  }
  const f = estado.ficha;
  const dudosos = new Set(f.campos_dudosos || []);
  const clase = (campo) => `campo ${dudosos.has(campo) ? "dudoso" : ""}`;
  const fichas = (nombre, opciones, elegidas) => `
    <fieldset class="campo" style="border:none;padding:0;margin:0"><span>${nombre}</span>
      <div class="chips" data-grupo="${nombre}">
        ${opciones.map((o) => `<button type="button" class="chip" aria-pressed="${elegidas.includes(o)}" data-valor="${esc(o)}">${esc(o)}</button>`).join("")}
      </div></fieldset>`;
  const distritos = [...catalogo.distritos, "Otro"];
  const distritoActual = distritos.includes(f.distrito_vivienda) ? f.distrito_vivienda : "Otro";
  const listaDudosos = [...new Set([...dudosos].map((c) => NOMBRES_CAMPO[c] || c))];

  raiz.innerHTML = `
  <div class="pantalla">
    <div class="barra">
      <button class="boton-redondo" type="button" id="volver" aria-label="Volver a las preguntas">${icono("atras", 22)}</button>
      <div style="flex-grow:1"><h1 style="font-size:26px">Revise su ficha</h1><span class="nota">Llenada con: ${esc(estado.metodo)}</span></div>
    </div>
    <div class="aviso">${icono("alerta", 22)}<span>
      ${listaDudosos.length ? `Confirme: <strong>${esc(listaDudosos.join(", "))}</strong>. ` : ""}
      Revise bien su <strong>nombre</strong>: a veces la voz no se entiende bien.</span></div>
    <form id="ficha" class="tarjeta" novalidate>
      <label class="${clase("nombre_completo")}"><span>Nombre completo</span><input name="nombre_completo" value="${esc(f.nombre_completo)}" autocomplete="off"></label>
      <div class="par">
        <label class="${clase("dni")}"><span>DNI</span><input name="dni" value="${esc(f.dni)}" inputmode="numeric" maxlength="8" autocomplete="off"></label>
        <label class="${clase("edad")}"><span>Edad</span><input name="edad" type="number" min="14" max="100" value="${esc(f.edad ?? "")}"></label>
      </div>
      <div class="par">
        <label class="${clase("distrito_vivienda")}"><span>Distrito</span>
          <select name="distrito_vivienda">${distritos.map((d) => `<option ${d === distritoActual ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></label>
        <label class="${clase("sector_vivienda")}"><span>Barrio</span><input name="sector_vivienda" value="${esc(f.sector_vivienda)}"></label>
      </div>
      ${fichas("Materiales", [...catalogo.materiales, "Otro"], f.materiales)}
      ${fichas("Recoge con", [...catalogo.transportes, "Otro"], f.medio_transporte)}
      <label class="casilla"><input type="checkbox" name="pertenece_asociacion" ${f.pertenece_asociacion ? "checked" : ""}> Pertenece a una asociación</label>
      <label class="campo"><span>¿Cuál asociación?</span><input name="nombre_asociacion" value="${esc(f.nombre_asociacion)}"></label>
      ${fichas("Protección", catalogo.equipos, f.equipo_proteccion)}
    </form>
    <div id="mensaje"></div>
    <button class="boton principal ancho" type="button" id="guardar">${icono("check", 22)} Todo está bien, inscribirme</button>
    <span class="nota" style="text-align:center">Recibirá su constancia en PDF</span>
  </div>`;

  raiz.querySelectorAll(".chips button").forEach((b) =>
    b.addEventListener("click", () => b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true")));
  raiz.querySelector("#volver").addEventListener("click", () => irA(raiz, catalogo.preguntas.length));
  raiz.querySelector("#guardar").addEventListener("click", async (e) => {
    const datos = new FormData(raiz.querySelector("#ficha"));
    const elegidos = (grupo) => [...raiz.querySelectorAll(`[data-grupo="${grupo}"] [aria-pressed="true"]`)].map((b) => b.dataset.valor);
    const dni = (datos.get("dni") || "").replace(/\D/g, "");
    const mensaje = raiz.querySelector("#mensaje");
    if (dni.length !== 8) {
      mensaje.innerHTML = `<div class="error" role="alert">El DNI debe tener 8 números.</div>`;
      return;
    }
    const ficha = {
      ...f,
      nombre_completo: datos.get("nombre_completo") || null,
      dni,
      edad: datos.get("edad") ? Number(datos.get("edad")) : null,
      distrito_vivienda: datos.get("distrito_vivienda"),
      sector_vivienda: datos.get("sector_vivienda") || null,
      materiales: elegidos("Materiales"),
      medio_transporte: elegidos("Recoge con"),
      pertenece_asociacion: datos.get("pertenece_asociacion") === "on",
      nombre_asociacion: datos.get("nombre_asociacion") || null,
      equipo_proteccion: elegidos("Protección"),
    };
    e.target.disabled = true;
    try {
      const { codigo } = await enviar("/recicladores", { ficha, metodo: estado.metodo });
      estado.ficha = ficha;
      estado.codigo = codigo;
      sesion.codigo = codigo; // desde ahora este celular sabe quién es
      cerrarMicrofono();
      dibujar(raiz);
    } catch (error) {
      e.target.disabled = false;
      mensaje.innerHTML = mensajeError(error);
    }
  });
}

// --- Final: inscrito ----------------------------------------------------------------------------
function dibujarFinal(raiz) {
  raiz.innerHTML = `
  <div class="pantalla" style="text-align:center">
    <div class="empuja"></div>
    <span style="width:96px;height:96px;border-radius:50%;background:var(--verde);color:#FFFFFF;display:grid;place-items:center;margin:0 auto">${icono("check", 52, 2.5)}</span>
    <h1>¡Ya está inscrito!</h1>
    <p class="subtitulo">Su código de registro es</p>
    <p style="font-size:34px;font-weight:700;letter-spacing:1px">${esc(estado.codigo)}</p>
    <div class="empuja"></div>
    <a class="boton principal ancho" href="${enlace(`/recicladores/${encodeURIComponent(estado.codigo)}/constancia`)}">${icono("descargar", 22)} Descargar mi constancia</a>
    <a class="boton ancho" href="#/reciclador">Ir a mi menú</a>
  </div>`;
}
