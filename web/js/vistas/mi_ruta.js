// Mi ruta: precios de hoy en su distrito y un mapa con los locales de acopio y los recojos.
import { leer } from "../api.js";
import { barra, cargando, esc, mensajeError, menuReciclador, nuevoMapa, pin, sesion, soles } from "../comun.js";

export async function mostrar(raiz) {
  if (!sesion.codigo) { location.hash = "#/reciclador"; return; }
  raiz.innerHTML = `<div class="pantalla con-menu">${cargando()}</div>${menuReciclador("mi-ruta")}`;
  let mapa = null;
  try {
    const yo = await leer(`/recicladores/${encodeURIComponent(sesion.codigo)}`);
    const distrito = yo.distrito_vivienda;
    const [precios, acopiosDistrito, recojos, catalogo] = await Promise.all([
      leer("/precios", { distrito }), leer("/acopios", { distrito }),
      leer("/recojos/disponibles", { codigo: yo.codigo }), leer("/catalogos"),
    ]);
    const acopios = acopiosDistrito.length ? acopiosDistrito : await leer("/acopios");

    raiz.innerHTML = `
    <div class="pantalla con-menu">
      ${barra("#/reciclador")}
      <header><span class="subtitulo">${esc(distrito)}</span><h1>Precios de hoy</h1></header>
      <div class="mapa" id="mapa" role="img" aria-label="Mapa con ${acopios.length} locales de acopio y ${recojos.length} recojos"></div>
      <div class="leyenda"><span style="--c:var(--verde)">Acopio</span><span style="--c:var(--naranja)">Reciclaje para recoger</span></div>
      <section style="display:flex;flex-direction:column;gap:8px">
        <h2>Mayor precio del día, por kilo</h2>
        ${precios.length ? `<div class="lista">${precios.map((p) => `
          <div class="fila">
            <div style="display:flex;flex-direction:column">
              <span class="principal">${esc(p.material)}</span>
              <span class="secundario">${esc(p.donde)} · último: ${soles(p.ultimo)} (${esc(p.hora)})</span>
            </div>
            <span class="precio">${soles(p.mayor)}</span>
          </div>`).join("")}</div>` : `<p class="vacio">Todavía no hay precios de hoy.</p>`}
        <p class="nota">Precios que ingresan los acopiadores en la app (datos inventados para el demo).</p>
      </section>
    </div>
    ${menuReciclador("mi-ruta", recojos.length)}`;

    mapa = nuevoMapa(raiz.querySelector("#mapa"), catalogo.centros[distrito] || catalogo.centros.Trujillo, 14);
    acopios.forEach((a) => L.marker([a.lat, a.lon], { icon: pin("acopio", "S/") })
      .bindPopup(`<strong>${esc(a.nombre)}</strong><br>${esc(a.direccion)}`).addTo(mapa));
    recojos.forEach((r) => L.marker([r.lat, r.lon], { icon: pin("recojo") })
      .bindPopup(`${esc(r.descripcion)} · ${Math.round(r.peso_kg)} kg${r.hora_desde ? `<br>De ${esc(r.hora_desde)} a ${esc(r.hora_hasta)}` : ""}`).addTo(mapa));
  } catch (error) {
    raiz.innerHTML = `<div class="pantalla con-menu">${barra("#/reciclador")}${mensajeError(error)}</div>${menuReciclador("mi-ruta")}`;
  }
  return () => mapa?.remove();
}
