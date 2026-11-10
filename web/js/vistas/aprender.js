// Aprender: buenas prácticas, cómo reconocer cada material, precios de campo y un quiz.
// Si acierta todo el quiz, queda marcado como «capacitado» en el registro.
import { enviar, leer } from "../api.js";
import { barra, cargando, esc, mensajeError, menuReciclador, sesion, soles } from "../comun.js";

const PESTANAS = ["Cuidados", "Materiales", "Precios", "Quiz"];

export async function mostrar(raiz, pestana = "Cuidados") {
  const conMenu = Boolean(sesion.codigo);
  const menu = conMenu ? menuReciclador("aprender") : "";
  raiz.innerHTML = `<div class="pantalla ${conMenu ? "con-menu" : ""}">${cargando()}</div>${menu}`;
  let contenido;
  try {
    contenido = await leer("/capacitacion");
  } catch (error) {
    raiz.innerHTML = `<div class="pantalla">${barra("#/")}${mensajeError(error)}</div>${menu}`;
    return;
  }

  const secciones = {
    Cuidados: () => contenido.modulos.map((m) => `
      <section class="tarjeta"><h2>${esc(m.titulo)}</h2>
        <ul style="margin:0;padding-left:22px;display:flex;flex-direction:column;gap:8px">${m.puntos.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>
      </section>`).join(""),
    Materiales: () => `<div class="lista">${contenido.materiales.map((m) => `
      <div class="fila" style="flex-direction:column;align-items:flex-start;gap:4px">
        <span class="principal">${esc(m.material)}</span>
        <span>${esc(m.como_reconocerlo)}</span>
        <span class="secundario">Consejo: ${esc(m.consejo)}</span>
      </div>`).join("")}</div>`,
    Precios: () => `
      <p class="subtitulo">Lo que pagan por kilo en El Porvenir, frente al precio de exportación del Perú.</p>
      <div class="lista">${contenido.precios_campo.map((p) => `
        <div class="fila">
          <div style="display:flex;flex-direction:column">
            <span class="principal">${esc(p.material)}</span>
            <span class="secundario">Exportación: ${soles(p.exportacion_soles_kg)}</span>
          </div>
          <span class="precio">${p.precio_min_soles_kg === p.precio_max_soles_kg ? soles(p.precio_min_soles_kg)
            : `${soles(p.precio_min_soles_kg)} a ${Number(p.precio_max_soles_kg).toFixed(2)}`}</span>
        </div>`).join("")}</div>
      <p class="nota">Fuentes: trabajo de campo de la tesis de la autora en El Porvenir (2026); UN Comtrade, exportaciones del Perú en 2025. El precio de exportación es de material clasificado y embalado: indica distancia, no margen.</p>`,
    Quiz: () => `
      <form id="quiz" class="tarjeta">
        <p>Responda las ${contenido.quiz.length} preguntas. Si acierta todas, queda marcado como <strong>capacitado</strong>.</p>
        ${contenido.quiz.map((q, i) => `
          <fieldset class="campo" style="border:none;padding:0;margin:0"><span>${i + 1}. ${esc(q.pregunta)}</span>
            ${q.opciones.map((o) => `<label class="casilla"><input type="radio" name="p${i}" value="${esc(o)}"> ${esc(o)}</label>`).join("")}
          </fieldset>`).join("")}
        <label class="campo"><span>Su código de registro</span><input name="codigo" value="${esc(sesion.codigo || "")}" placeholder="RMR-2026-0061"></label>
        <button class="boton principal" type="submit">Revisar respuestas</button>
        <div id="resultado"></div>
      </form>`,
  };

  raiz.innerHTML = `
  <div class="pantalla ${conMenu ? "con-menu" : ""}">
    ${barra(conMenu ? "#/reciclador" : "#/")}
    <h1>Aprender</h1>
    <div class="pestanas" role="tablist">
      ${PESTANAS.map((p) => `<button type="button" role="tab" aria-selected="${p === pestana}" data-pestana="${p}">${p}</button>`).join("")}
    </div>
    <div style="display:flex;flex-direction:column;gap:14px" role="tabpanel">${secciones[pestana]()}</div>
  </div>
  ${menu}`;

  raiz.querySelectorAll("[data-pestana]").forEach((b) =>
    b.addEventListener("click", () => mostrar(raiz, b.dataset.pestana)));

  raiz.querySelector("#quiz")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const datos = new FormData(e.target);
    const respuestas = contenido.quiz.map((_, i) => datos.get(`p${i}`));
    const resultado = raiz.querySelector("#resultado");
    try {
      const r = await enviar("/quiz", { respuestas, codigo: datos.get("codigo") || null });
      resultado.innerHTML = `
        <div class="${r.aciertos === r.total ? "exito" : "aviso"}" role="status">
          Acertó <strong>${r.aciertos} de ${r.total}</strong>.
          ${r.correcciones.map((c) => `<br>${esc(c.pregunta)} → <strong>${esc(c.correcta)}</strong>`).join("")}
          ${r.capacitado ? "<br><strong>¡Felicitaciones! Quedó marcado como capacitado.</strong>" : ""}
          ${r.aciertos === r.total && !r.capacitado ? "<br>Escriba un código de registro válido para que quede anotado." : ""}
        </div>`;
    } catch (error) {
      resultado.innerHTML = mensajeError(error);
    }
  });
}
