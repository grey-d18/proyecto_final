// Recoger reciclaje: pedidos de los vecinos. «Lo recogeré» lo asigna por 3 días; si no se
// recoge en ese plazo, vuelve a estar disponible para otro reciclador de la zona.
import { enlace, enviar, leer } from "../api.js";
import { barra, cargando, esc, hablar, icono, mensajeError, menuReciclador, sesion } from "../comun.js";

export async function mostrar(raiz, aviso = false) {
  if (!sesion.codigo) { location.hash = "#/reciclador"; return; }
  if (!aviso) raiz.innerHTML = `<div class="pantalla con-menu">${cargando()}</div>${menuReciclador("recoger")}`;
  try {
    const yo = await leer(`/recicladores/${encodeURIComponent(sesion.codigo)}`);
    const [disponibles, mios] = await Promise.all([
      leer("/recojos/disponibles", { codigo: yo.codigo }), leer("/recojos/mios", { codigo: yo.codigo }),
    ]);

    const limite = (fecha) => {
      const d = new Date(fecha.replace(" ", "T"));
      d.setDate(d.getDate() + 3);
      return d.toLocaleString("es-PE", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
    };
    const foto = (r) => r.tiene_foto
      ? `<img src="${enlace(`/recojos/${r.id}/foto`)}" alt="Foto del reciclaje" style="width:100%;max-height:220px;object-fit:cover;border-radius:14px">` : "";

    raiz.innerHTML = `
    <div class="pantalla con-menu">
      ${barra("#/reciclador")}
      <h1>Recoger reciclaje</h1>
      ${aviso ? `<div class="aviso" role="alert">${icono("alerta", 22)}<span>Recuerde que tiene un máximo de <strong>3 días</strong> para hacer su recojo. Si no, se asignará a otro reciclador de la zona.</span></div>` : ""}

      <h2>Para recoger en ${esc(yo.distrito_vivienda)}</h2>
      ${disponibles.length ? disponibles.map((r) => `
        <article class="tarjeta">
          ${foto(r)}
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline">
            <strong style="font-size:20px">${esc(r.descripcion)}</strong>
            <span class="chip">${Math.round(r.peso_kg)} kg</span>
          </div>
          <span class="subtitulo">${esc(r.vecino)} · ${esc(r.direccion || r.distrito)}</span>
          <button class="boton principal" type="button" data-tomar="${r.id}">${icono("check", 22)} Lo recogeré</button>
        </article>`).join("") : `<p class="vacio">Por ahora no hay reciclaje para recoger en su zona.</p>`}

      ${mios.length ? `<h2>Mis recojos</h2>
        <div class="lista">${mios.map((r) => `
          <div class="fila">
            <div style="display:flex;flex-direction:column">
              <span class="principal">${esc(r.descripcion)} · ${Math.round(r.peso_kg)} kg</span>
              <span class="secundario">${esc(r.direccion || r.distrito)} · hasta el ${limite(r.fecha_asignacion)}</span>
            </div>
            <button class="boton chico suave" type="button" data-hecho="${r.id}">Ya lo recogí</button>
          </div>`).join("")}</div>` : ""}
    </div>
    ${menuReciclador("recoger", disponibles.length)}`;

    raiz.querySelectorAll("[data-tomar]").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      await enviar(`/recojos/${b.dataset.tomar}/asignar`, { codigo: yo.codigo });
      hablar("aviso_recojo");
      mostrar(raiz, true);
    }));
    raiz.querySelectorAll("[data-hecho]").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      await enviar(`/recojos/${b.dataset.hecho}/recogido`, {});
      mostrar(raiz);
    }));
  } catch (error) {
    raiz.innerHTML = `<div class="pantalla con-menu">${barra("#/reciclador")}${mensajeError(error)}</div>${menuReciclador("recoger")}`;
  }
}
