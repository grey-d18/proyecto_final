// «¿Dónde está?»: dos formas de ubicar un local o un pedido.
//   1. Usar mi ubicación: el GPS del celular (el navegador pide permiso). Hay que estar en el lugar.
//   2. Escribir la dirección: la API la busca en OpenStreetMap; si no la encuentra,
//      usa el centro del distrito.
import { leer } from "./api.js";
import { esc, icono } from "./comun.js";

// Dibuja los botones dentro de «contenedor». distrito() devuelve el distrito elegido en ese momento.
// Devuelve una función que entrega { direccion, lat, lon } o null si todavía no hay ubicación.
export function elegirUbicacion(contenedor, distrito, avisoGps) {
  let lugar = null;
  contenedor.innerHTML = `
    <div class="par">
      <button class="boton chico" type="button" data-modo="gps">${icono("ubicacion", 20)} Usar mi ubicación</button>
      <button class="boton chico" type="button" data-modo="escribir">${icono("lapiz", 20)} Escribir dirección</button>
    </div>
    <div data-detalle style="display:flex;flex-direction:column;gap:10px"></div>`;
  const detalle = contenedor.querySelector("[data-detalle]");
  const listo = (texto, tipo = "exito") => { detalle.insertAdjacentHTML("beforeend", `<div class="${tipo}" role="status">${texto}</div>`); };

  contenedor.querySelector('[data-modo="gps"]').addEventListener("click", () => {
    lugar = null;
    detalle.innerHTML = `<p class="nota">${esc(avisoGps)}</p>`;
    if (!navigator.geolocation) return listo("Este navegador no puede dar la ubicación. Escriba la dirección.", "error");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        lugar = { direccion: "Ubicación del GPS", lat: p.coords.latitude, lon: p.coords.longitude };
        listo(`Ubicación lista (${lugar.lat.toFixed(4)}, ${lugar.lon.toFixed(4)})`);
      },
      () => listo("El navegador no dio la ubicación. Revise el permiso o escriba la dirección.", "error"),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  });

  contenedor.querySelector('[data-modo="escribir"]').addEventListener("click", () => {
    lugar = null;
    detalle.innerHTML = `
      <label class="campo"><span>Dirección o referencia</span><input data-direccion placeholder="Av. Pumacahua 1450"></label>
      <button class="boton chico suave" type="button" data-buscar>Buscar en el mapa</button>`;
    detalle.querySelector("[data-buscar]").addEventListener("click", async () => {
      const direccion = detalle.querySelector("[data-direccion]").value.trim();
      if (!direccion) return;
      detalle.querySelectorAll(".exito,.aviso,.error").forEach((n) => n.remove());
      try {
        const r = await leer("/ubicacion", { direccion, distrito: distrito() });
        lugar = { direccion, lat: r.lat, lon: r.lon };
        r.encontrada ? listo("Encontramos la dirección en el mapa.")
          : listo("No encontramos esa dirección en el mapa: usaremos el centro del distrito.", "aviso");
      } catch (error) {
        listo(esc(error.message), "error");
      }
    });
  });

  return () => lugar;
}
