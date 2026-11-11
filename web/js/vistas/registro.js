// Registro por voz: el flujo principal del producto.
//   Paso 0      bienvenida, aviso de grabación y consentimiento: dice o toca «sí, acepto» (ahí se abre el micrófono).
//   Preguntas   6 preguntas abiertas, una por pantalla. Después de cada respuesta, la API llena la
//               ficha con todo lo dicho y decide la siguiente (POST /entrevista): si ya se dijo un
//               dato, su pregunta se salta; si falta, se repregunta una sola vez.
//   Ficha       la persona revisa su ficha, la escucha (con los dígitos del DNI uno por uno) y
//               dice «sí, acepto»: es su declaración jurada, y se guarda con la hora.
//   Final       código de registro y constancia en PDF.
import { enlace, enviar, enviarFormulario, leer } from "../api.js";
import { barra, callar, cargando, esc, hablar, icono, leerFichaEnVoz, mensajeError, precargar, sesion } from "../comun.js";
import { abrirMicrofono, cerrarMicrofono, grabar, microfonoAbierto } from "../grabadora.js";

let catalogo = null;
// Lo que se va respondiendo. Vive mientras la página esté abierta (si vuelve atrás, no se pierde).
//   historial: las preguntas que se fueron haciendo (cambia según lo que la persona dice)
//   paso:      0 = bienvenida; 1… = la pregunta historial[paso - 1]; después, la ficha
const nuevo = () => ({ paso: 0, historial: [], respuestas: {}, saltadas: [], yaSaltadas: [], ficha: null, metodo: "", codigo: null });
const estado = nuevo();
const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
// Para avisar qué pregunta se saltó porque la persona ya lo había dicho.
const LO_QUE_PIDE = {
  dni: "su DNI", nombre_nacimiento: "su nombre y su fecha de nacimiento", vivienda_celular: "dónde vive y su celular",
  trabajo: "sus materiales, zona y horario", equipo: "con qué recoge su material",
  asociacion: "si está en una asociación",
};
let grabacion = null;
const MIENTRAS_HABLA = "Le escuchamos… Toque el cuadrado cuando termine";

export async function mostrar(raiz) {
  if (estado.codigo) Object.assign(estado, nuevo());
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  catalogo ??= await leer("/catalogos");
  // Descarga ya todas las voces del registro, para que ninguna se entrecorte al sonar.
  precargar(["bienvenida_registro", ...catalogo.preguntas.map((p) => p.clave), "resumen_inicio", "resumen_final",
    "re_dni", "re_nombre", "re_nacimiento", "re_genero", "re_direccion", "re_celular", "re_materiales", "re_zona", "re_horario", "re_equipo"]);
  dibujar(raiz);
  return () => { grabacion?.detener(); cerrarMicrofono(); };
}

function dibujar(raiz) {
  if (estado.codigo) return dibujarFinal(raiz);
  if (estado.paso === 0) return dibujarBienvenida(raiz);
  if (estado.paso <= estado.historial.length) return dibujarPregunta(raiz);
  return dibujarFicha(raiz);
}

const irA = (raiz, paso) => { callar(); grabacion?.detener(); estado.paso = paso; window.scrollTo(0, 0); dibujar(raiz); };

// --- Paso 0 ------------------------------------------------------------------------------
// Para aceptar, la persona dice «sí, acepto» (como en la declaración jurada del final),
// o toca «Prefiero tocar: Sí, acepto».
function dibujarBienvenida(raiz) {
  raiz.innerHTML = `
  <div class="pantalla">
    ${barra(sesion.codigo ? "#/reciclador" : "#/")}
    <h1>Registro de recicladores</h1>
    <div class="tarjeta">
      <button class="boton chico suave" type="button" id="escuchar" style="align-self:flex-start">${icono("parlante", 20)} Escuchar</button>
      <p>Le haremos <strong>${catalogo.preguntas.length} preguntas</strong>. Escuche cada una y responda hablando.</p>
      <p class="subtitulo">Sus datos solo se usan para el Registro Municipal de Recicladores (Ley 29419).</p>
      <p class="subtitulo"><strong>Aviso:</strong> su voz se graba solo para convertirla en texto y llenar su ficha;
        el audio no se guarda. Sus datos están protegidos por la Ley 29733.</p>
    </div>
    <p style="margin:0;font-weight:700;text-align:center">Acepto registrarme y que se usen mis datos para el registro.</p>
    <div class="zona-micro" id="zona-acepto" style="min-height:0"></div>
  </div>`;
  const zona = raiz.querySelector("#zona-acepto");
  raiz.querySelector("#escuchar").addEventListener("click", () => hablar("bienvenida_registro"));

  const empezar = async () => {
    callar();
    if (!microfonoAbierto()) {
      try {
        await abrirMicrofono(); // el navegador pide permiso aquí, una sola vez
      } catch {
        // Sin micrófono igual se puede seguir: las respuestas se escriben.
        zona.innerHTML = `<div class="aviso">${icono("alerta", 22)}<span>No pudimos usar el micrófono. Puede escribir las respuestas, o dar permiso al micrófono en el navegador.</span></div>`;
        await new Promise((r) => setTimeout(r, 1800));
      }
    }
    if (!estado.historial.length) estado.historial = [catalogo.preguntas[0]];
    irA(raiz, 1);
  };

  const dibujarAcepto = (aviso = "") => {
    zona.innerHTML = `
      ${aviso ? `<div class="aviso">${icono("alerta", 22)}<span>${aviso}</span></div>` : ""}
      <button class="micro" type="button" id="decir" aria-label="Tocar y decir: sí, acepto" style="color:#FFFFFF">${icono("micro", 56, 1.8)}</button>
      <span style="font-size:20px;font-weight:700">Toque y diga «sí, acepto»</span>
      <button class="enlace" type="button" id="empezar">Prefiero tocar: Sí, acepto</button>`;
    zona.querySelector("#empezar").addEventListener("click", empezar);
    zona.querySelector("#decir").addEventListener("click", async () => {
      callar();
      if (!microfonoAbierto()) {
        try { await abrirMicrofono(); } catch { return dibujarAcepto("No pudimos usar el micrófono. Toque «Sí, acepto»."); }
      }
      zona.innerHTML = `
        <button class="micro grabando" type="button" id="parar" aria-label="Terminar" style="color:#FFFFFF">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button><span style="font-size:20px;font-weight:700">Diga: «sí, acepto»</span>`;
      grabacion = grabar({ segundos: 10 });
      zona.querySelector("#parar").addEventListener("click", () => grabacion?.detener());
      const { audio, extension } = await grabacion.terminado;
      grabacion = null;
      if (!document.body.contains(zona)) return;
      zona.innerHTML = `<div class="girando" role="status" aria-label="Escuchando"></div>`;
      try {
        const formulario = new FormData();
        formulario.append("audio", audio, `acepto${extension}`);
        const { texto } = await enviarFormulario("/transcribir", formulario);
        if (/acepto/i.test(texto)) return empezar();
        dibujarAcepto(texto.trim() ? `Escuchamos «${esc(texto.trim())}». Para empezar, diga «sí, acepto».` : "No escuchamos nada. Hable cerca del celular.");
      } catch (error) {
        dibujarAcepto(esc(error.message));
      }
    });
  };
  dibujarAcepto();
  hablar("bienvenida_registro"); // la bienvenida se escucha sola (la persona acaba de tocar un botón)
}

// --- Preguntas -------------------------------------------------------------------------------
function dibujarPregunta(raiz) {
  const total = catalogo.preguntas.length;
  const pregunta = estado.historial[estado.paso - 1];
  const clave = pregunta.clave;
  const delGuion = catalogo.preguntas.findIndex((p) => p.clave === clave);
  const hechas = delGuion >= 0 ? delGuion + 1 : total; // en las repreguntas, la barra ya está llena
  const titulo = delGuion >= 0 ? `Pregunta ${delGuion + 1} de ${total}` : "Una pregunta más";
  const saltadas = estado.paso === estado.historial.length ? estado.saltadas : [];

  raiz.innerHTML = `
  <div class="pantalla">
    <div style="display:flex;flex-direction:column;gap:12px">
      ${barra("#/registro", titulo).replace('href="#/registro"', 'href="#/registro" id="volver"')}
      <div class="progreso" style="--total:${total}" aria-hidden="true">
        ${catalogo.preguntas.map((_, i) => `<span class="${i < hechas ? "hecho" : ""}"></span>`).join("")}
      </div>
    </div>
    ${saltadas.length ? `<p class="nota" role="status">${icono("check", 16)} Ya nos dijo ${esc(saltadas.map((c) => LO_QUE_PIDE[c] || c).join(" y "))}: no se lo volvemos a preguntar.</p>` : ""}
    <section class="tarjeta pregunta">
      <button class="boton chico suave" type="button" id="escuchar" style="align-self:flex-start">${icono("parlante", 20)} Escuchar otra vez</button>
      <h1>${esc(pregunta.texto)}</h1>
      <p class="subtitulo">Por ejemplo: «${esc(pregunta.ejemplo)}»</p>
    </section>
    <div class="zona-micro" id="zona"></div>
    <div id="mensaje"></div>
    <div class="par">
      <button class="boton" type="button" id="anterior">Anterior</button>
      <button class="boton principal" type="button" id="siguiente">Siguiente</button>
    </div>
  </div>`;

  const zona = raiz.querySelector("#zona");
  let escribiendo = false;
  let agregando = false; // «Agregar más»: lo nuevo se suma a lo que ya dijo

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
        <span class="etiqueta" id="cuenta" role="status" style="font-size:20px;font-weight:700">${MIENTRAS_HABLA}</span>`;
    } else if (modo === "escuchando") {
      zona.innerHTML = `<div class="girando" role="status" aria-label="Entendiendo su respuesta"></div><p class="subtitulo">Entendiendo su respuesta…</p>`;
    } else if (respuesta) {
      zona.innerHTML = `
        <div class="entendimos">
          <span class="nota" style="font-weight:700">Entendimos:</span>
          <span class="texto">${esc(respuesta)}</span>
          <div class="chips">
            <button class="boton chico" type="button" id="agregar">${icono("micro", 20)} Agregar más</button>
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
    zona.querySelector("#agregar")?.addEventListener("click", () => { agregando = true; tocarMicro(); });
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
    const anterior = agregando ? (estado.respuestas[clave] || "") : "";
    agregando = false;
    dibujarZona("grabando");
    const barras = [...zona.querySelectorAll(".onda span")];
    const cuenta = zona.querySelector("#cuenta");
    grabacion = grabar({
      segundos: pregunta.segundos,
      alCambiarVolumen: (v) => barras.forEach((b, i) => {
        b.style.height = `${Math.min(36, 8 + v * 400 * (0.5 + ((i * 7) % 5) / 5))}px`;
      }),
      // Antes de cortar por silencio, avisa: «¿Terminó? Termino en 3…». Si vuelve a hablar, sigue.
      alContar: (n) => { cuenta.textContent = n ? `¿Terminó? Termino en ${n}…` : MIENTRAS_HABLA; },
    });
    const { audio, extension } = await grabacion.terminado;
    grabacion = null;
    if (!document.body.contains(zona)) return; // la persona salió de la pantalla
    dibujarZona("escuchando");
    try {
      const formulario = new FormData();
      formulario.append("audio", audio, `respuesta${extension}`);
      const { texto } = await enviarFormulario("/transcribir", formulario);
      if (texto.trim()) {
        estado.respuestas[clave] = [anterior, texto.trim()].filter(Boolean).join(" ");
        dibujarZona();
      } else if (anterior) {
        dibujarZona(); // no se escuchó nada nuevo: queda lo que ya había dicho
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
  raiz.querySelector("#siguiente").addEventListener("click", (e) => siguiente(raiz, e.target));
}

// Envía todo lo dicho hasta esta pregunta y la API responde qué preguntar después.
async function siguiente(raiz, boton) {
  callar();
  grabacion?.detener();
  boton.disabled = true;
  boton.textContent = "Revisando…";
  // Si volvió atrás y cambió una respuesta, lo que venía después se vuelve a decidir.
  const historial = estado.historial.slice(0, estado.paso);
  const hechas = historial.map((p) => p.clave);
  const respuestas = Object.fromEntries(hechas.map((c) => [c, estado.respuestas[c] || ""]));
  try {
    const paso = await enviar("/entrevista", { respuestas, hechas });
    estado.historial = historial;
    estado.respuestas = respuestas;
    // Solo se avisa de las que se saltaron recién (no se repite el aviso en cada pregunta).
    estado.saltadas = paso.saltadas.filter((c) => !estado.yaSaltadas.includes(c));
    estado.yaSaltadas = paso.saltadas;
    estado.ficha = paso.ficha;
    estado.metodo = paso.metodo;
    if (paso.siguiente) estado.historial.push(paso.siguiente);
    irA(raiz, estado.paso + 1); // si no hay siguiente, esto lleva a la ficha
  } catch (error) {
    boton.disabled = false;
    boton.textContent = "Siguiente";
    raiz.querySelector("#mensaje").innerHTML = mensajeError(error);
  }
}

// --- Revisar la ficha y declarar ---------------------------------------------------------------
const NOMBRES_CAMPO = {
  nombre_completo: "nombre", dni: "DNI", fecha_nacimiento: "fecha de nacimiento", genero: "género",
  direccion: "dirección", distrito_vivienda: "distrito", telefono: "celular", materiales: "materiales",
  zona_trabajo: "zona", dias_trabajo: "días", horario: "horario", equipo: "con qué trabaja",
};
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
  "octubre", "noviembre", "diciembre"];

function edad(fecha) {
  if (!fecha) return "";
  const [a, m, d] = fecha.split("-").map(Number);
  const hoy = new Date();
  return hoy.getFullYear() - a - ((hoy.getMonth() + 1 < m || (hoy.getMonth() + 1 === m && hoy.getDate() < d)) ? 1 : 0);
}

// Los datos de la ficha que lee la voz del celular (el inicio y el final los dice Camila).
// El DNI y el celular, dígito por dígito, para que la persona confirme que se entendió bien.
function resumen(f) {
  const digitos = (t) => (t || "").split("").join(", ");
  const lista = (l) => (l || []).join(", ").toLowerCase();
  const partes = [`Nombre: ${f.nombre_completo || "por completar"}.`,
    f.dni ? `DNI: ${digitos(f.dni)}.` : "DNI: por completar."];
  if (f.genero) partes.push(f.genero === "Femenino" ? "Mujer." : "Hombre.");
  if (f.fecha_nacimiento) {
    const [a, m, d] = f.fecha_nacimiento.split("-").map(Number);
    partes.push(`Nació el ${d} de ${MESES[m - 1]} de ${a}.`);
  }
  if (f.direccion) partes.push(`Vive en ${f.direccion}.`);
  if (f.telefono) partes.push(`Celular: ${digitos(f.telefono)}.`);
  if (f.materiales?.length) partes.push(`Recoge ${lista(f.materiales)}.`);
  if (f.zona_trabajo) partes.push(`En ${f.zona_trabajo}.`);
  if (f.dias_trabajo?.length) partes.push(`Los días ${lista(f.dias_trabajo)}${f.hora_desde ? `, de ${f.hora_desde} a ${f.hora_hasta}` : ""}.`);
  const con = [...(f.medio_transporte || []), ...(f.equipo_proteccion || [])];
  if (con.length) partes.push(`Trabaja con ${lista(con)}.`);
  if (f.pertenece_asociacion === true) partes.push(f.nombre_asociacion ? `Está en la asociación ${f.nombre_asociacion}.` : "Está en una asociación.");
  if (f.pertenece_asociacion === false) partes.push("No está en una asociación.");
  return partes.join(" ");
}

function dibujarFicha(raiz) {
  const f = estado.ficha;
  const dudosos = new Set(f.campos_dudosos || []);
  const faltan = new Set(f.faltantes || []);
  const clase = (campo) => `campo ${dudosos.has(campo) || faltan.has(campo) ? "dudoso" : ""}`;
  const etiqueta = (texto, campo) => `<span>${texto}${faltan.has(campo) ? ' <em style="font-weight:400">· por completar</em>' : ""}</span>`;
  const fichas = (nombre, campo, opciones, elegidas) => `
    <fieldset class="campo" style="border:none;padding:0;margin:0">${etiqueta(nombre, campo)}
      <div class="chips" data-grupo="${nombre}">
        ${opciones.map((o) => `<button type="button" class="chip" aria-pressed="${(elegidas || []).includes(o)}" data-valor="${esc(o)}">${esc(o)}</button>`).join("")}
      </div></fieldset>`;
  const distritos = [...catalogo.distritos, "Otro"];
  const distritoActual = distritos.includes(f.distrito_vivienda) ? f.distrito_vivienda : "Otro";
  const revisar = [...new Set([...dudosos].map((c) => NOMBRES_CAMPO[c] || c))];
  const pendientes = [...faltan].map((c) => NOMBRES_CAMPO[c] || c);

  raiz.innerHTML = `
  <div class="pantalla">
    <div class="barra">
      <button class="boton-redondo" type="button" id="volver" aria-label="Volver a las preguntas">${icono("atras", 22)}</button>
      <div style="flex-grow:1"><h1 style="font-size:26px">Revise su ficha</h1><span class="nota">Llenada con: ${esc(estado.metodo)} · ${estado.historial.length} preguntas</span></div>
    </div>
    <div class="aviso">${icono("alerta", 22)}<span>
      ${revisar.length ? `Confirme: <strong>${esc(revisar.join(", "))}</strong>. ` : ""}
      ${pendientes.length ? `Quedan <strong>por completar</strong>: ${esc(pendientes.join(", "))}. Puede escribirlos ahora o completarlos después en la municipalidad. ` : ""}
      Revise bien su <strong>nombre</strong>: a veces la voz no se entiende bien.</span></div>
    <form id="ficha" class="tarjeta" novalidate>
      <label class="${clase("nombre_completo")}">${etiqueta("Nombre completo", "nombre_completo")}<input name="nombre_completo" value="${esc(f.nombre_completo)}" autocomplete="off"></label>
      <label class="${clase("dni")}">${etiqueta("DNI", "dni")}<input name="dni" value="${esc(f.dni)}" inputmode="numeric" maxlength="8" autocomplete="off">
        <span class="nota" id="dni-digitos" style="letter-spacing:4px"></span></label>
      <div class="par">
        <label class="${clase("fecha_nacimiento")}">${etiqueta("Fecha de nacimiento", "fecha_nacimiento")}<input name="fecha_nacimiento" type="date" value="${esc(f.fecha_nacimiento)}"></label>
        <label class="campo"><span>Edad</span><input id="edad" value="${esc(edad(f.fecha_nacimiento))}" readonly tabindex="-1"></label>
      </div>
      <label class="${clase("genero")}">${etiqueta("Género", "genero")}
        <select name="genero">${["", "Femenino", "Masculino"].map((g) => `<option value="${g}" ${g === (f.genero || "") ? "selected" : ""}>${g || "—"}</option>`).join("")}</select></label>
      <label class="${clase("direccion")}">${etiqueta("Dirección", "direccion")}<input name="direccion" value="${esc(f.direccion)}"></label>
      <label class="${clase("distrito_vivienda")}"><span>Distrito</span>
        <select name="distrito_vivienda">${distritos.map((d) => `<option ${d === distritoActual ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></label>
      <div class="par">
        <label class="${clase("telefono")}">${etiqueta("Celular", "telefono")}<input name="telefono" value="${esc(f.telefono)}" inputmode="numeric" maxlength="9"></label>
        <label class="campo"><span>Correo (opcional)</span><input name="correo" type="email" value="${esc(f.correo)}"></label>
      </div>
      <div class="par">
        <label class="campo"><span>¿Está en una asociación?</span>
          <select name="pertenece_asociacion">${[["", "—"], ["si", "Sí"], ["no", "No"]].map(([v, t]) => `<option value="${v}" ${v === (f.pertenece_asociacion === true ? "si" : f.pertenece_asociacion === false ? "no" : "") ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <label class="campo"><span>Nombre de la asociación</span><input name="nombre_asociacion" value="${esc(f.nombre_asociacion)}"></label>
      </div>
      <label class="campo"><span>Cargo en su organización</span><input name="cargo" value="${esc(f.cargo || "socio")}"></label>
      ${fichas("Materiales", "materiales", [...catalogo.materiales, "Otro"], f.materiales)}
      <label class="${clase("zona_trabajo")}">${etiqueta("Zona donde recoge", "zona_trabajo")}<input name="zona_trabajo" value="${esc(f.zona_trabajo)}"></label>
      ${fichas("Días", "dias_trabajo", DIAS, f.dias_trabajo)}
      <div class="par">
        <label class="${clase("horario")}">${etiqueta("Desde", "horario")}<input name="hora_desde" type="time" value="${esc(f.hora_desde)}"></label>
        <label class="${clase("horario")}"><span>Hasta</span><input name="hora_hasta" type="time" value="${esc(f.hora_hasta)}"></label>
      </div>
      ${fichas("Vehículo", "equipo", [...catalogo.transportes, "Otro"], f.medio_transporte)}
      ${fichas("Protección", "equipo", catalogo.equipos, f.equipo_proteccion)}
    </form>

    <section class="tarjeta" aria-labelledby="titulo-declaracion">
      <h2 id="titulo-declaracion" style="margin:0">Declaración jurada</h2>
      <p class="subtitulo" style="margin:0">Declaro que mis datos son verdaderos. Para inscribirse, escuche su ficha y diga <strong>«sí, acepto»</strong>.</p>
      <button class="boton chico suave" type="button" id="escuchar-ficha" style="align-self:flex-start">${icono("parlante", 20)} Escuchar mi ficha</button>
      <div class="zona-micro" id="zona-acepto" style="min-height:0"></div>
    </section>
    <div id="mensaje"></div>
  </div>`;

  const form = raiz.querySelector("#ficha");
  const dniDigitos = raiz.querySelector("#dni-digitos");
  const mostrarDigitos = () => { dniDigitos.textContent = (form.dni.value || "").replace(/\D/g, "").split("").join(" "); };
  mostrarDigitos();
  form.dni.addEventListener("input", mostrarDigitos);
  form.fecha_nacimiento.addEventListener("change", () => { raiz.querySelector("#edad").value = edad(form.fecha_nacimiento.value); });
  raiz.querySelectorAll(".chips button").forEach((b) =>
    b.addEventListener("click", () => b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true")));
  raiz.querySelector("#volver").addEventListener("click", () => irA(raiz, estado.historial.length));

  // La ficha tal como está en pantalla (con lo que la persona corrigió).
  const leerFicha = () => {
    const datos = new FormData(form);
    const elegidos = (grupo) => [...raiz.querySelectorAll(`[data-grupo="${grupo}"] [aria-pressed="true"]`)].map((b) => b.dataset.valor);
    const texto = (c) => (datos.get(c) || "").trim() || null;
    return {
      ...f,
      nombre_completo: texto("nombre_completo"),
      dni: (datos.get("dni") || "").replace(/\D/g, ""),
      fecha_nacimiento: texto("fecha_nacimiento"),
      genero: texto("genero"),
      direccion: texto("direccion"),
      distrito_vivienda: datos.get("distrito_vivienda"),
      telefono: (datos.get("telefono") || "").replace(/\D/g, "") || null,
      correo: texto("correo"),
      cargo: texto("cargo") || "socio",
      pertenece_asociacion: { si: true, no: false }[datos.get("pertenece_asociacion")] ?? null,
      nombre_asociacion: datos.get("pertenece_asociacion") === "si" ? texto("nombre_asociacion") : null,
      materiales: elegidos("Materiales"),
      zona_trabajo: texto("zona_trabajo"),
      dias_trabajo: elegidos("Días"),
      hora_desde: texto("hora_desde"),
      hora_hasta: texto("hora_hasta"),
      medio_transporte: elegidos("Vehículo"),
      equipo_proteccion: elegidos("Protección"),
    };
  };
  raiz.querySelector("#escuchar-ficha").addEventListener("click", () => leerFichaEnVoz("resumen_inicio", resumen(leerFicha()), "resumen_final"));

  const mensaje = raiz.querySelector("#mensaje");
  const zona = raiz.querySelector("#zona-acepto");

  async function inscribir(declaracion) {
    const ficha = leerFicha();
    if (ficha.dni.length !== 8) {
      mensaje.innerHTML = `<div class="error" role="alert">El DNI debe tener 8 números.</div>`;
      return dibujarAcepto();
    }
    if (ficha.telefono && !/^9\d{8}$/.test(ficha.telefono)) {
      mensaje.innerHTML = `<div class="error" role="alert">El celular debe tener 9 números y empezar con 9.</div>`;
      return dibujarAcepto();
    }
    zona.innerHTML = `<div class="girando" role="status" aria-label="Inscribiendo"></div>`;
    try {
      const { codigo } = await enviar("/recicladores", { ficha, metodo: estado.metodo, declaracion });
      estado.ficha = ficha;
      estado.codigo = codigo;
      sesion.codigo = codigo; // desde ahora este celular sabe quién es
      cerrarMicrofono();
      dibujar(raiz);
    } catch (error) {
      mensaje.innerHTML = mensajeError(error);
      dibujarAcepto();
    }
  }

  function dibujarAcepto(aviso = "") {
    zona.innerHTML = `
      ${aviso ? `<div class="aviso">${icono("alerta", 22)}<span>${aviso}</span></div>` : ""}
      <button class="micro" type="button" id="decir" aria-label="Tocar y decir: sí, acepto" style="color:#FFFFFF">${icono("micro", 56, 1.8)}</button>
      <span style="font-size:20px;font-weight:700">Toque y diga «sí, acepto»</span>
      <button class="enlace" type="button" id="tocar">Prefiero tocar: Sí, acepto</button>`;
    zona.querySelector("#tocar").addEventListener("click", () => inscribir("Sí, acepto (tocó el botón)"));
    zona.querySelector("#decir").addEventListener("click", async () => {
      callar();
      mensaje.innerHTML = "";
      if (!microfonoAbierto()) {
        try { await abrirMicrofono(); } catch { return dibujarAcepto("No pudimos usar el micrófono. Toque «Sí, acepto»."); }
      }
      zona.innerHTML = `
        <button class="micro grabando" type="button" id="parar" aria-label="Terminar" style="color:#FFFFFF">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button><span style="font-size:20px;font-weight:700">Diga: «sí, acepto»</span>`;
      grabacion = grabar({ segundos: 10 });
      zona.querySelector("#parar").addEventListener("click", () => grabacion?.detener());
      const { audio, extension } = await grabacion.terminado;
      grabacion = null;
      if (!document.body.contains(zona)) return;
      zona.innerHTML = `<div class="girando" role="status" aria-label="Escuchando"></div>`;
      try {
        const formulario = new FormData();
        formulario.append("audio", audio, `acepto${extension}`);
        const { texto } = await enviarFormulario("/transcribir", formulario);
        if (/acepto/i.test(texto)) return inscribir(texto.trim());
        dibujarAcepto(texto.trim() ? `Escuchamos «${esc(texto.trim())}». Para inscribirse, diga «sí, acepto».` : "No escuchamos nada. Hable cerca del celular.");
      } catch (error) {
        dibujarAcepto(esc(error.message));
      }
    });
  }

  dibujarAcepto();
  leerFichaEnVoz("resumen_inicio", resumen(f), "resumen_final"); // puede no sonar si el navegador lo bloquea: queda el botón «Escuchar mi ficha»
}

// --- Final: inscrito ----------------------------------------------------------------------------
function dibujarFinal(raiz) {
  // Ya se inscribió: que nada siga leyendo la ficha. En algunos Android la voz del celular
  // vuelve a sonar después de usar el micrófono, por eso se calla otra vez un momento después.
  callar();
  setTimeout(() => { try { speechSynthesis.cancel(); } catch { /* sin voz */ } }, 800);
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
