// Vecino: primero se inscribe (nombre, dirección, correo y teléfono) y después pide recojos.
// Al pedir un recojo dice CUÁNDO puede pasar el reciclador: con su voz («lunes y miércoles de 7
// a 9») o eligiendo los días y las horas. La voz pasa por Whisper y el LLM la convierte en horario.
import { enviar, enviarFormulario, leer } from "../api.js";
import { barra, cargando, esc, hablar, icono, mensajeError } from "../comun.js";
import { abrirMicrofono, cerrarMicrofono, grabar, microfonoAbierto } from "../grabadora.js";
import { elegirUbicacion } from "../ubicacion.js";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const CLAVE = "ecobarrio.vecino.codigo";
const guardarCodigo = (codigo) => { try { localStorage.setItem(CLAVE, codigo); } catch { /* modo privado */ } };
const leerCodigo = () => { try { return localStorage.getItem(CLAVE) || ""; } catch { return ""; } };
const olvidarCodigo = () => { try { localStorage.removeItem(CLAVE); } catch { /* modo privado */ } };

// «Lun, Mié, Vie · 07:00 a 09:00»
export function textoHorario(r) {
  const dias = Array.isArray(r.dias) ? r.dias : [];
  const cortos = dias.length === 7 ? "Todos los días" : dias.map((d) => d.slice(0, 3)).join(", ");
  const horas = r.hora_desde && r.hora_hasta ? `${r.hora_desde} a ${r.hora_hasta}` : "";
  return [cortos, horas].filter(Boolean).join(" · ");
}

let grabacion = null;

export async function mostrar(raiz) {
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  const catalogo = await leer("/catalogos");
  let vecino = null;
  const codigo = leerCodigo();
  if (codigo) {
    try { vecino = await leer(`/vecinos/${encodeURIComponent(codigo)}`); } catch { olvidarCodigo(); }
  }
  if (vecino) pedirRecojo(raiz, catalogo, vecino);
  else inscribirse(raiz, catalogo);
  return () => { grabacion?.detener(); cerrarMicrofono(); };
}

// --- 1. Inscripción -------------------------------------------------------------------------
function inscribirse(raiz, catalogo) {
  raiz.innerHTML = `
  <div class="pantalla">
    ${barra("#/")}
    <header><span class="subtitulo">Vecinos que reciclan</span><h1>Inscríbase una vez</h1></header>
    <p>Con su inscripción, los recicladores de su zona pueden recoger lo que usted separa. Solo se hace una vez.</p>
    <form id="inscripcion" class="tarjeta" novalidate>
      <label class="campo"><span>Nombre y apellido</span><input name="nombre" autocomplete="name" placeholder="Carmen Díaz"></label>
      <label class="campo"><span>Distrito</span>
        <select name="distrito">${catalogo.distritos.map((d) => `<option ${d === "El Porvenir" ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></label>
      <fieldset class="campo" style="border:none;padding:0;margin:0"><span>Su dirección</span><div id="ubicacion" style="display:flex;flex-direction:column;gap:10px"></div></fieldset>
      <label class="campo"><span>Correo</span><input name="correo" type="email" autocomplete="email" inputmode="email" placeholder="carmen@correo.com"></label>
      <label class="campo"><span>Celular</span><input name="telefono" type="tel" autocomplete="tel" inputmode="numeric" maxlength="9" placeholder="987654321"></label>
      <label style="display:flex;gap:10px;align-items:flex-start;font-size:17px">
        <input type="checkbox" name="acepto" style="width:24px;height:24px;flex:none;margin-top:2px">
        <span>Acepto que la Municipalidad guarde mis datos para coordinar los recojos. Mi celular solo lo verá el
        reciclador que acepte mi pedido, y solo si yo lo permito.</span></label>
      <div id="mensaje"></div>
      <button class="boton principal" type="submit">${icono("check", 22)} Inscribirme</button>
    </form>
  </div>`;

  const formulario = raiz.querySelector("#inscripcion");
  const ubicacion = elegirUbicacion(raiz.querySelector("#ubicacion"), () => formulario.elements.distrito.value,
    "Debe estar en su casa para usar su ubicación.");

  formulario.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = formulario.elements;
    const mensaje = raiz.querySelector("#mensaje");
    const aviso = (texto) => { mensaje.innerHTML = `<div class="error" role="alert">${texto}</div>`; };
    const lugar = ubicacion();
    const telefono = f.telefono.value.replace(/\D/g, "");
    if (f.nombre.value.trim().length < 2) return aviso("Escriba su nombre.");
    if (!lugar) return aviso("Falta su dirección: use su ubicación o escríbala.");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.correo.value.trim())) return aviso("Revise su correo.");
    if (!/^9\d{8}$/.test(telefono)) return aviso("El celular debe tener 9 números y empezar con 9.");
    if (!f.acepto.checked) return aviso("Para inscribirse tiene que aceptar que la Municipalidad guarde sus datos.");
    try {
      const { codigo } = await enviar("/vecinos", {
        nombre: f.nombre.value.trim(), distrito: f.distrito.value, direccion: lugar.direccion,
        lat: lugar.lat, lon: lugar.lon, correo: f.correo.value.trim(), telefono, acepto: true,
      });
      guardarCodigo(codigo);
      mostrar(raiz);
    } catch (error) {
      mensaje.innerHTML = mensajeError(error);
    }
  });
}

// --- 2. Pedir un recojo -----------------------------------------------------------------------
function pedirRecojo(raiz, catalogo, vecino) {
  const elegidos = new Set();
  raiz.innerHTML = `
  <div class="pantalla">
    ${barra("#/")}
    <header><span class="subtitulo">Hola, ${esc(vecino.nombre)}</span><h1>Pedir un recojo</h1></header>
    <form id="pedido" class="tarjeta" novalidate>
      <label class="campo"><span>¿Qué tiene para reciclar?</span><input name="descripcion" placeholder="Cajas de cartón y botellas"></label>
      <label class="campo"><span>Peso aproximado (kg)</span><input name="peso_kg" type="number" min="0" max="500" step="1" value="5" inputmode="decimal"></label>
      <label class="campo"><span>Foto (opcional)</span><input name="foto" type="file" accept="image/*" capture="environment"></label>

      <div class="campo"><span>¿Dónde se recoge?</span>
        <p style="margin:0">${icono("ubicacion", 18)} ${esc(vecino.direccion)}</p>
        <label style="display:flex;gap:8px;align-items:center;font-size:17px"><input type="checkbox" id="otra" style="width:22px;height:22px"> Está en otra dirección</label>
        <div id="ubicacion" style="display:none;flex-direction:column;gap:10px"></div>
      </div>

      <fieldset class="campo" style="border:none;padding:0;margin:0">
        <span>¿Cuándo puede pasar el reciclador?</span>
        <p class="nota" style="margin:0">Por ejemplo: «Lunes, miércoles y viernes de 7 a 9 de la mañana»</p>
        <div id="voz" style="display:flex;flex-direction:column;gap:8px;align-items:flex-start"></div>
        <div class="chips" role="group" aria-label="Días">
          ${DIAS.map((d) => `<button type="button" class="chip" aria-pressed="false" data-dia="${d}">${d}</button>`).join("")}
        </div>
        <div class="par">
          <label class="campo"><span class="nota">Desde</span><input name="hora_desde" type="time" step="900"></label>
          <label class="campo"><span class="nota">Hasta</span><input name="hora_hasta" type="time" step="900"></label>
        </div>
      </fieldset>

      <label style="display:flex;gap:10px;align-items:flex-start;font-size:17px">
        <input type="checkbox" name="compartir_telefono" value="true" style="width:24px;height:24px;flex:none;margin-top:2px">
        <span>Compartir mi celular (${esc(vecino.telefono)}) con el reciclador que acepte mi pedido, para coordinar.</span></label>
      <label class="campo"><span>¿Quién lo recoge?</span><select name="preferido" id="recicladores"></select></label>
      <div id="mensaje"></div>
      <button class="boton principal" type="submit">${icono("camion", 22)} Pedir recojo</button>
    </form>
    <section id="mis-pedidos" style="display:flex;flex-direction:column;gap:8px"></section>
    <button class="enlace" type="button" id="no-soy">No soy ${esc(vecino.nombre)}</button>
  </div>`;

  const formulario = raiz.querySelector("#pedido");
  let otraUbicacion = null;
  raiz.querySelector("#otra").addEventListener("change", (e) => {
    const caja = raiz.querySelector("#ubicacion");
    caja.style.display = e.target.checked ? "flex" : "none";
    if (e.target.checked && !otraUbicacion) {
      otraUbicacion = elegirUbicacion(caja, () => vecino.distrito, "Debe estar en el lugar donde está el reciclaje.");
    }
  });
  raiz.querySelector("#no-soy").addEventListener("click", () => { olvidarCodigo(); mostrar(raiz); });

  // Días: botones que se prenden y se apagan
  const pintarDias = () => raiz.querySelectorAll("[data-dia]").forEach((b) => b.setAttribute("aria-pressed", elegidos.has(b.dataset.dia)));
  raiz.querySelectorAll("[data-dia]").forEach((b) => b.addEventListener("click", () => {
    elegidos.has(b.dataset.dia) ? elegidos.delete(b.dataset.dia) : elegidos.add(b.dataset.dia);
    pintarDias();
  }));

  // Horario dicho con la voz → Whisper → LLM → días y horas (que la persona puede corregir)
  const voz = raiz.querySelector("#voz");
  let dicho = "";
  const pintarVoz = (modo = "esperando", texto = "") => {
    if (modo === "grabando") {
      voz.innerHTML = `<button class="boton principal" type="button" id="hablar">${icono("check", 20)} Ya terminé</button>
        <span id="cuenta" role="status" style="font-weight:700">Le escuchamos…</span>`;
    } else if (modo === "entendiendo") {
      voz.innerHTML = `<p class="subtitulo" role="status">Entendiendo su horario…</p>`;
    } else {
      voz.innerHTML = `${texto ? `<div class="${modo === "error" ? "aviso" : "entendimos"}"><span>${texto}</span></div>` : ""}
        <button class="boton" type="button" id="hablar">${icono("micro", 20)} ${dicho ? "Decirlo otra vez" : "Decirlo con mi voz"}</button>`;
    }
    voz.querySelector("#hablar")?.addEventListener("click", tocarMicro);
  };

  async function tocarMicro() {
    if (grabacion) return grabacion.detener();
    if (!microfonoAbierto()) {
      try { await abrirMicrofono(); } catch {
        return pintarVoz("error", "No pudimos usar el micrófono. Elija los días y las horas abajo.");
      }
    }
    pintarVoz("grabando");
    const cuenta = voz.querySelector("#cuenta");
    grabacion = grabar({ segundos: 30, alContar: (n) => { cuenta.textContent = n ? `¿Terminó? Termino en ${n}…` : "Le escuchamos…"; } });
    const { audio, extension } = await grabacion.terminado;
    grabacion = null;
    if (!document.body.contains(voz)) return;
    pintarVoz("entendiendo");
    try {
      const formularioAudio = new FormData();
      formularioAudio.append("audio", audio, `horario${extension}`);
      const { texto } = await enviarFormulario("/transcribir", formularioAudio);
      if (!texto.trim()) return pintarVoz("error", "No escuchamos nada. Hable cerca del celular o elija los días abajo.");
      dicho = texto.trim();
      const horario = await enviar("/horario", { texto: dicho });
      elegidos.clear();
      horario.dias.forEach((d) => elegidos.add(d));
      pintarDias();
      if (horario.hora_desde) formulario.elements.hora_desde.value = horario.hora_desde;
      if (horario.hora_hasta) formulario.elements.hora_hasta.value = horario.hora_hasta;
      const falta = !horario.dias.length || !horario.hora_desde ? " Complete lo que falta abajo." : " Puede corregirlo abajo.";
      pintarVoz("listo", `Entendimos: «${esc(dicho)}».${falta}`);
    } catch (error) {
      pintarVoz("error", esc(error.message));
    }
  }
  pintarVoz();
  hablar("horario_recojo");

  // Recicladores del distrito del vecino
  leer("/recicladores", { distrito: vecino.distrito }).then((lista) => {
    raiz.querySelector("#recicladores").innerHTML = `<option value="">Cualquiera de la zona</option>` +
      lista.map((r) => `<option value="${esc(r.codigo)}">${esc(r.nombre_completo)}</option>`).join("");
  });

  const misPedidos = async () => {
    const pedidos = await leer("/recojos", { vecino_codigo: vecino.codigo });
    const estados = { disponible: "Esperando reciclador", asignado: "Un reciclador viene", recogido: "Recogido" };
    raiz.querySelector("#mis-pedidos").innerHTML = pedidos.length ? `<h2>Mis pedidos</h2><div class="lista">${pedidos.map((p) => `
      <div class="fila"><div style="display:flex;flex-direction:column"><span class="principal">${esc(p.descripcion)}</span>
        <span class="secundario">${esc(p.fecha_hora)} · ${Math.round(p.peso_kg)} kg · ${esc(textoHorario(p))}</span></div>
        <span class="chip">${esc(estados[p.estado] || p.estado)}</span></div>`).join("")}</div>` : "";
  };
  misPedidos();

  formulario.addEventListener("submit", async (e) => {
    e.preventDefault();
    const mensaje = raiz.querySelector("#mensaje");
    const aviso = (texto) => { mensaje.innerHTML = `<div class="error" role="alert">${texto}</div>`; };
    const datos = new FormData(formulario);
    if (!datos.get("descripcion")) return aviso("Escriba qué tiene para reciclar.");
    if (!elegidos.size) return aviso("Diga o elija los días en que pueden pasar.");
    const desde = datos.get("hora_desde");
    const hasta = datos.get("hora_hasta");
    if (!desde || !hasta || desde >= hasta) return aviso("Revise el horario: la hora «hasta» tiene que ser después de «desde».");
    let lugar = { direccion: vecino.direccion, lat: vecino.lat, lon: vecino.lon };
    if (raiz.querySelector("#otra").checked) {
      lugar = otraUbicacion?.();
      if (!lugar) return aviso("Falta la otra dirección: use su ubicación o escríbala.");
    }
    datos.set("vecino_codigo", vecino.codigo);
    datos.set("direccion", lugar.direccion);
    datos.set("lat", lugar.lat);
    datos.set("lon", lugar.lon);
    datos.set("dias", JSON.stringify(DIAS.filter((d) => elegidos.has(d))));
    datos.set("horario_dicho", dicho);
    datos.set("compartir_telefono", formulario.elements.compartir_telefono.checked ? "true" : "false");
    if (!datos.get("foto")?.size) datos.delete("foto");
    try {
      await enviarFormulario("/recojos", datos);
      mensaje.innerHTML = `<div class="exito" role="status">Listo. Los recicladores de la zona ya pueden ver su pedido.</div>`;
      misPedidos();
    } catch (error) {
      mensaje.innerHTML = mensajeError(error);
    }
  });
}
