// Vecino: pide que recojan su reciclaje (qué es, cuánto pesa, foto y dónde está).
import { enviarFormulario, leer } from "../api.js";
import { barra, cargando, esc, icono, mensajeError } from "../comun.js";
import { elegirUbicacion } from "../ubicacion.js";

const CLAVE = "reciclavoz.vecino";
const recordar = (nombre) => { try { localStorage.setItem(CLAVE, nombre); } catch { /* modo privado */ } };
const recordado = () => { try { return localStorage.getItem(CLAVE) || ""; } catch { return ""; } };

export async function mostrar(raiz) {
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  const catalogo = await leer("/catalogos");

  raiz.innerHTML = `
  <div class="pantalla">
    ${barra("#/")}
    <h1>Pedir un recojo</h1>
    <form id="pedido" class="tarjeta" novalidate>
      <label class="campo"><span>Su nombre</span><input name="vecino" value="${esc(recordado())}" placeholder="Carmen Díaz" autocomplete="name"></label>
      <label class="campo"><span>¿Qué tiene para reciclar?</span><input name="descripcion" placeholder="Cajas de cartón y botellas"></label>
      <div class="par">
        <label class="campo"><span>Peso aproximado (kg)</span><input name="peso_kg" type="number" min="0" max="500" step="1" value="5" inputmode="decimal"></label>
        <label class="campo"><span>Distrito</span>
          <select name="distrito">${catalogo.distritos.map((d) => `<option ${d === "El Porvenir" ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></label>
      </div>
      <label class="campo"><span>Foto (opcional)</span><input name="foto" type="file" accept="image/*" capture="environment"></label>
      <fieldset class="campo" style="border:none;padding:0;margin:0"><span>¿Dónde está el reciclaje?</span><div id="ubicacion" style="display:flex;flex-direction:column;gap:10px"></div></fieldset>
      <label class="campo"><span>¿Quién lo recoge?</span><select name="preferido" id="recicladores"></select></label>
      <div id="mensaje"></div>
      <button class="boton principal" type="submit">${icono("camion", 22)} Pedir recojo</button>
    </form>
    <section id="mis-pedidos" style="display:flex;flex-direction:column;gap:8px"></section>
  </div>`;

  const formulario = raiz.querySelector("#pedido");
  const distrito = () => formulario.elements.distrito.value;
  const ubicacion = elegirUbicacion(raiz.querySelector("#ubicacion"), distrito, "Debe estar en el lugar donde está el reciclaje.");

  const cargarRecicladores = async () => {
    const lista = await leer("/recicladores", { distrito: distrito() });
    raiz.querySelector("#recicladores").innerHTML = `<option value="">Cualquiera de la zona</option>` +
      lista.map((r) => `<option value="${esc(r.codigo)}">${esc(r.nombre_completo)}</option>`).join("");
  };
  formulario.elements.distrito.addEventListener("change", cargarRecicladores);
  await cargarRecicladores();

  const misPedidos = async (nombre) => {
    if (!nombre) return;
    const pedidos = await leer("/recojos", { vecino: nombre });
    const estados = { disponible: "Esperando reciclador", asignado: "Un reciclador viene", recogido: "Recogido" };
    raiz.querySelector("#mis-pedidos").innerHTML = pedidos.length ? `<h2>Mis pedidos</h2><div class="lista">${pedidos.map((p) => `
      <div class="fila"><div style="display:flex;flex-direction:column"><span class="principal">${esc(p.descripcion)}</span>
        <span class="secundario">${esc(p.fecha_hora)} · ${Math.round(p.peso_kg)} kg</span></div>
        <span class="chip">${esc(estados[p.estado] || p.estado)}</span></div>`).join("")}</div>` : "";
  };
  misPedidos(recordado());

  formulario.addEventListener("submit", async (e) => {
    e.preventDefault();
    const mensaje = raiz.querySelector("#mensaje");
    const datos = new FormData(formulario);
    const lugar = ubicacion();
    if (!datos.get("vecino") || !datos.get("descripcion")) {
      mensaje.innerHTML = `<div class="error" role="alert">Escriba su nombre y qué tiene para reciclar.</div>`;
      return;
    }
    if (!lugar) {
      mensaje.innerHTML = `<div class="error" role="alert">Falta la ubicación: use su ubicación o escriba la dirección.</div>`;
      return;
    }
    datos.set("direccion", lugar.direccion);
    datos.set("lat", lugar.lat);
    datos.set("lon", lugar.lon);
    if (!datos.get("foto")?.size) datos.delete("foto");
    try {
      await enviarFormulario("/recojos", datos);
      recordar(datos.get("vecino"));
      mensaje.innerHTML = `<div class="exito" role="status">Listo. Los recicladores de la zona ya pueden ver su pedido.</div>`;
      misPedidos(datos.get("vecino"));
    } catch (error) {
      mensaje.innerHTML = mensajeError(error);
    }
  });
}
