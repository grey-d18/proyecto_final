// Inicio del reciclador. Si el celular ya sabe quién es, lo saluda; si no, pregunta.
import { enlace, leer } from "../api.js";
import { barra, cargando, esc, icono, mensajeError, menuReciclador, sesion } from "../comun.js";

export async function mostrar(raiz) {
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  try {
    if (!sesion.codigo) return await preguntarQuienEs(raiz);
    let yo;
    try {
      yo = await leer(`/recicladores/${encodeURIComponent(sesion.codigo)}`);
    } catch {
      sesion.codigo = null; // el código guardado ya no existe (por ejemplo, se reinició el demo)
      return await preguntarQuienEs(raiz);
    }
    const pendientes = (await leer("/recojos/disponibles", { codigo: yo.codigo })).length;
    const nombre = (yo.nombre_completo || "").split(" ")[0];

    const opcion = (ruta, titulo, detalle, ico, extra = "") => `
      <a class="opcion" href="${ruta}">
        <span class="icono" style="color:var(--verde)">${icono(ico, 30, 1.8)}</span>
        <span class="textos"><span class="titulo">${titulo} ${extra}</span><span class="detalle">${detalle}</span></span>
        ${icono("adelante", 24)}
      </a>`;

    raiz.innerHTML = `
    <div class="pantalla con-menu">
      ${barra("#/")}
      <div style="display:flex;flex-direction:column;gap:4px">
        <h1>Hola, ${esc(nombre)}</h1>
        <p class="subtitulo">Su código: <strong>${esc(yo.codigo)}</strong> · ${esc(yo.distrito_vivienda || "")}</p>
      </div>
      <nav class="opciones">
        ${opcion("#/mi-ruta", "Mi ruta", "Precios de hoy y dónde vender", "mapa")}
        ${opcion("#/recoger", "Recoger reciclaje", "Pedidos de los vecinos", "camion",
                 pendientes ? `<span class="globo">${pendientes}</span>` : "")}
        ${opcion("#/aprender", "Aprender", "Cuidados, materiales y quiz", "libro")}
        ${opcion(enlace(`/recicladores/${encodeURIComponent(yo.codigo)}/constancia`), "Mi constancia", "Descargar en PDF", "documento")}
      </nav>
      <button class="enlace" type="button" id="no-soy">No soy ${esc(nombre)}</button>
    </div>
    ${menuReciclador("reciclador", pendientes)}`;

    raiz.querySelector("#no-soy").addEventListener("click", () => {
      sesion.codigo = null;
      mostrar(raiz);
    });
  } catch (error) {
    raiz.innerHTML = `<div class="pantalla">${barra("#/")}${mensajeError(error)}</div>`;
  }
}

async function preguntarQuienEs(raiz) {
  // En el demo varias personas usan el mismo celular: proponemos al último inscrito.
  const ultimo = await leer("/recicladores/ultimo");
  raiz.innerHTML = `
  <div class="pantalla">
    ${barra("#/")}
    ${ultimo ? `
      <h1 style="text-align:center;margin-top:24px">¿Es usted ${esc(ultimo.nombre_completo)}?</h1>
      <div class="par">
        <button class="boton principal" type="button" id="si">Sí, soy yo</button>
        <a class="boton" href="#/registro">No</a>
      </div>` : ""}
    <div class="empuja"></div>
    <a class="boton ${ultimo ? "" : "principal"} ancho" href="#/registro">${icono("micro", 22)} Inscribirme por primera vez</a>
  </div>`;
  raiz.querySelector("#si")?.addEventListener("click", () => {
    sesion.codigo = ultimo.codigo;
    mostrar(raiz);
  });
}
