// Acopiador: elige (o registra) su local y publica sus precios del día.
// Con esos precios se arma «Mi ruta» de los recicladores.
import { enviar, leer } from "../api.js";
import { barra, cargando, esc, icono, mensajeError } from "../comun.js";
import { elegirUbicacion } from "../ubicacion.js";

const AVISO_LOCAL = "Usted tiene que estar en su local para usar esta opción.";
const CLAVE = "reciclavoz.acopio";
const recordar = (id) => { try { localStorage.setItem(CLAVE, id); } catch { /* modo privado */ } };
const recordado = () => { try { return localStorage.getItem(CLAVE); } catch { return null; } };

export async function mostrar(raiz, elegido = recordado()) {
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  const [catalogo, acopios] = await Promise.all([leer("/catalogos"), leer("/acopios")]);
  const acopio = acopios.find((a) => String(a.id) === String(elegido)) || (elegido === "nuevo" ? null : acopios[0]);

  raiz.innerHTML = `
  <div class="pantalla">
    ${barra("#/")}
    <h1>Acopiador</h1>
    <label class="campo"><span>Su local</span>
      <select id="local">
        ${acopios.map((a) => `<option value="${a.id}" ${acopio && a.id === acopio.id ? "selected" : ""}>${esc(a.nombre)} · ${esc(a.distrito)}</option>`).join("")}
        <option value="nuevo" ${acopio ? "" : "selected"}>Mi local no está en la lista</option>
      </select></label>
    <div id="contenido" style="display:flex;flex-direction:column;gap:18px"></div>
  </div>`;
  raiz.querySelector("#local").addEventListener("change", (e) => { recordar(e.target.value); mostrar(raiz, e.target.value); });
  const contenido = raiz.querySelector("#contenido");
  if (!acopio) return registrarLocal(raiz, contenido, catalogo);
  await publicarPrecios(raiz, contenido, catalogo, acopio);
}

function registrarLocal(raiz, contenido, catalogo) {
  contenido.innerHTML = `
    <form class="tarjeta" id="nuevo" novalidate>
      <h2>Registrar mi local</h2>
      <label class="campo"><span>Nombre del local</span><input name="nombre" placeholder="Reciclajes Doña Rosa"></label>
      <label class="campo"><span>Distrito</span>
        <select name="distrito">${catalogo.distritos.map((d) => `<option ${d === "El Porvenir" ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></label>
      <fieldset class="campo" style="border:none;padding:0;margin:0"><span>¿Dónde está su local?</span><div id="ubicacion" style="display:flex;flex-direction:column;gap:10px"></div></fieldset>
      <div id="mensaje"></div>
      <button class="boton principal" type="submit">Guardar mi local</button>
    </form>`;
  const formulario = contenido.querySelector("#nuevo");
  const ubicacion = elegirUbicacion(contenido.querySelector("#ubicacion"), () => formulario.elements.distrito.value, AVISO_LOCAL);
  formulario.addEventListener("submit", async (e) => {
    e.preventDefault();
    const lugar = ubicacion();
    const nombre = formulario.elements.nombre.value.trim();
    if (!nombre || !lugar) {
      contenido.querySelector("#mensaje").innerHTML = `<div class="error" role="alert">Falta el nombre del local o la ubicación.</div>`;
      return;
    }
    try {
      const { id } = await enviar("/acopios", { nombre, distrito: formulario.elements.distrito.value, ...lugar });
      recordar(id);
      mostrar(raiz, id);
    } catch (error) {
      contenido.querySelector("#mensaje").innerHTML = mensajeError(error);
    }
  });
}

async function publicarPrecios(raiz, contenido, catalogo, acopio) {
  const actuales = await leer(`/acopios/${acopio.id}/precios`);
  contenido.innerHTML = `
    <p class="subtitulo">${icono("ubicacion", 18)} ${esc(acopio.direccion)} · ${esc(acopio.distrito)}</p>
    <form class="tarjeta" id="precios">
      <h2>Mis precios de hoy (S/ por kilo)</h2>
      <p class="nota">Deje en 0 los materiales que no compra.</p>
      <div class="rejilla-precios">
        ${catalogo.materiales.map((m) => `
          <label class="campo"><span>${esc(m)}</span>
            <input name="${esc(m)}" type="number" min="0" max="100" step="0.05" inputmode="decimal" value="${(actuales[m] ?? 0).toFixed(2)}"></label>`).join("")}
      </div>
      <div id="mensaje"></div>
      <button class="boton principal" type="submit">Publicar precios</button>
    </form>
    <details class="tarjeta"><summary style="cursor:pointer;font-weight:700;min-height:32px">Cambiar la ubicación de mi local</summary>
      <div id="ubicacion" style="display:flex;flex-direction:column;gap:10px;margin-top:12px"></div>
      <button class="boton chico" type="button" id="guardar-ubicacion" style="margin-top:10px">Guardar ubicación</button>
      <div id="mensaje-ubicacion"></div>
    </details>`;

  contenido.querySelector("#precios").addEventListener("submit", async (e) => {
    e.preventDefault();
    const precios = Object.fromEntries(catalogo.materiales.map((m) => [m, Number(e.target.elements[m].value) || 0]));
    try {
      await enviar(`/acopios/${acopio.id}/precios`, { precios });
      contenido.querySelector("#mensaje").innerHTML = `<div class="exito" role="status">Precios publicados. Los recicladores ya los ven en «Mi ruta».</div>`;
    } catch (error) {
      contenido.querySelector("#mensaje").innerHTML = mensajeError(error);
    }
  });

  const ubicacion = elegirUbicacion(contenido.querySelector("#ubicacion"), () => acopio.distrito, AVISO_LOCAL);
  contenido.querySelector("#guardar-ubicacion").addEventListener("click", async () => {
    const lugar = ubicacion();
    const salida = contenido.querySelector("#mensaje-ubicacion");
    if (!lugar) { salida.innerHTML = `<div class="error" role="alert">Primero elija la ubicación.</div>`; return; }
    await enviar(`/acopios/${acopio.id}/ubicacion`, lugar, "PUT");
    mostrar(raiz, acopio.id);
  });
}
