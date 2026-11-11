// Panel municipal: lo que pasa en la app (recicladores, vecinos, acopios y recojos), con un
// resumen del mes que se ofrece al entrar. Los datos personales llegan ocultos desde la API.
import { leer } from "../api.js";
import { esc, cargando, icono, logo, mensajeError, nuevoMapa, pin } from "../comun.js";

const elegidos = new Set(); // distritos del filtro (vacío = todos)
const SIGERSOL = "https://sistemas.minam.gob.pe/SigersolMunicipal/";
const DATOS_ABIERTOS = "https://www.datosabiertos.gob.pe/";

const nombreMes = (mes) => {
  const [anio, numero] = mes.split("-").map(Number);
  const texto = new Date(anio, numero - 1, 1).toLocaleDateString("es-PE", { month: "long", year: "numeric" });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
};
const fecha = (texto) => esc((texto || "").slice(0, 10));
const lista = (v) => (Array.isArray(v) ? v.join(", ") : v ?? "");

// La ventana del resumen se ofrece una vez por visita (no cada vez que se filtra).
const yaOfrecido = () => { try { return sessionStorage.getItem("ecobarrio.resumen") === "1"; } catch { return false; } };
const marcarOfrecido = () => { try { sessionStorage.setItem("ecobarrio.resumen", "1"); } catch { /* modo privado */ } };

export async function mostrar(raiz) {
  raiz.innerHTML = `<div class="pantalla">${cargando()}</div>`;
  let mapa = null;
  let datos;
  try {
    datos = await leer("/panel", { distritos: [...elegidos].join(",") });
  } catch (error) {
    raiz.innerHTML = `<div class="pantalla"><a class="boton" href="#/">Volver</a>${mensajeError(error)}</div>`;
    return;
  }
  const k = datos.indicadores;
  const barras = (filas, color) => {
    const max = Math.max(1, ...filas.map(([, n]) => n));
    return `<div class="barras" style="--c:${color}">${filas.map(([nombre, n]) => `
      <span>${esc(nombre)}</span><div class="barra-dato" style="width:${(n / max) * 100}%"></div><span class="numero">${n}</span>`).join("")}</div>`;
  };
  const indicador = (nombre, valor, clase = "") =>
    `<div class="indicador ${clase}"><span class="nombre">${nombre}</span><span class="valor">${valor}</span></div>`;

  raiz.innerHTML = `
  <div class="panel">
    <aside>
      <a class="marca" href="#/" style="color:#FFFFFF;padding:0">${logo}<span style="display:flex;flex-direction:column;line-height:1.2">EcoBarrio<span style="font-size:13px;font-weight:400;color:#B8C4BC">Municipalidad de Trujillo</span></span></a>
      <nav aria-label="Panel">
        ${[["resumen", "Resumen"], ["recicladores", "Recicladores"], ["mapa-panel", "Mapa"], ["acopios", "Acopios"],
           ["vecinos", "Vecinos"], ["recojos", "Recojos"], ["sigersol", "SIGERSOL"]]
          .map(([id, texto]) => `<a href="#/municipalidad" data-ir="${id}">${texto}</a>`).join("")}
        <a href="#/">Salir</a>
      </nav>
    </aside>
    <main>
      <header id="resumen" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap">
        <div><h1>Reciclaje en la provincia</h1><p class="subtitulo">Lo que pasa en EcoBarrio · datos sintéticos + lo registrado en el demo</p></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="boton chico" type="button" id="ver-mes">${icono("grafico", 18)} Resumen del mes</button>
          <button class="boton chico principal" type="button" id="csv">${icono("descargar", 18)} Descargar CSV</button>
        </div>
      </header>
      <div class="chips" aria-label="Filtrar por distrito">
        ${datos.todos_los_distritos.map((d) => `<button type="button" class="chip" aria-pressed="${elegidos.has(d)}" data-distrito="${esc(d)}">${esc(d)}</button>`).join("")}
      </div>
      <section class="indicadores" aria-label="Resumen">
        ${indicador("Recicladores inscritos", k.recicladores)}
        ${indicador("Vecinos inscritos", k.vecinos)}
        ${indicador("Locales de acopio", k.acopios)}
        ${indicador("Recojos hechos", k.recojos_recogidos)}
        ${indicador("Kilos recogidos", k.kg_recogidos.toLocaleString("es-PE"))}
      </section>

      <h2 id="recicladores">Recicladores</h2>
      <section class="indicadores" aria-label="Recicladores">
        ${indicador("En una asociación", `${k.en_asociacion} %`)}
        ${indicador("Capacitados", `${k.capacitados} %`)}
        ${indicador("Sin guantes", `${k.sin_guantes} %`)}
        ${indicador("Solo con saco (necesitan equipo)", k.solo_saco, "alerta")}
      </section>
      <section class="dos-columnas">
        <div class="tarjeta"><h2>Dónde viven</h2>${barras(datos.por_distrito.filter((d) => d.recicladores).sort((a, b) => b.recicladores - a.recicladores).map((d) => [d.distrito, d.recicladores]), "var(--verde)")}</div>
        <div class="tarjeta"><h2>Qué recogen <span class="nota">(personas)</span></h2>${barras(datos.materiales.map((m) => [m.material, m.personas]), "var(--azul)")}</div>
      </section>

      <section class="tarjeta" id="mapa-panel">
        <h2>Recicladores y locales de acopio</h2>
        <div class="leyenda"><span style="--c:var(--verde)">Recicladores por distrito (más grande, más inscritos)</span><span style="--c:var(--verde-oscuro)">Local de acopio</span></div>
        <div class="mapa alto" id="mapa"></div>
      </section>

      <section class="tarjeta" id="acopios">
        <h2>Locales de acopio</h2>
        <div class="tabla-caja"><table>
          <thead><tr><th>Local</th><th>Distrito</th><th>Dirección</th><th>Compra</th><th>Precios actualizados</th></tr></thead>
          <tbody>${datos.acopios.map((a) => `<tr><td><strong>${esc(a.nombre)}</strong></td><td>${esc(a.distrito)}</td><td>${esc(a.direccion)}</td>
            <td>${esc(lista(a.compra))}</td><td class="sin-corte">${esc(a.ultima_actualizacion || "Nunca")}</td></tr>`).join("")}</tbody>
        </table></div>
      </section>

      <section class="tarjeta" id="vecinos">
        <h2>Vecinos que reciclan</h2>
        <div class="dos-columnas">
          <div>${barras(datos.por_distrito.filter((d) => d.vecinos).sort((a, b) => b.vecinos - a.vecinos).map((d) => [d.distrito, d.vecinos]), "var(--naranja)")}</div>
          <div class="tabla-caja con-limite"><table>
            <thead><tr><th>Código</th><th>Nombre</th><th>Distrito</th><th>Celular</th><th>Correo</th><th>Pedidos</th></tr></thead>
            <tbody>${datos.vecinos.map((v) => `<tr><td class="sin-corte"><strong>${esc(v.codigo)}</strong></td><td>${esc(v.nombre)}</td><td>${esc(v.distrito)}</td>
              <td class="sin-corte">${esc(v.telefono)}</td><td class="sin-corte">${esc(v.correo)}</td><td>${v.pedidos}</td></tr>`).join("")}</tbody>
          </table></div>
        </div>
        <p class="nota">El celular y el correo se muestran ocultos. El celular completo solo lo ve el reciclador que acepta un pedido, si el vecino lo permite.</p>
      </section>

      <section class="tarjeta" id="recojos">
        <h2>Recojos</h2>
        <section class="indicadores" aria-label="Recojos">
          ${indicador("Pedidos", k.recojos_pedidos)}
          ${indicador("Recogidos", k.recojos_recogidos)}
          ${indicador("Esperando o en camino", datos.recojos.pendientes)}
        </section>
        <div class="dos-columnas">
          <div><h3>¿A qué hora piden que pasen?</h3>${barras(datos.recojos.por_franja.map((f) => [f.franja, f.pedidos]), "var(--naranja)")}</div>
          <div><h3>¿Qué días?</h3>${barras(datos.recojos.por_dia.map((d) => [d.dia, d.pedidos]), "var(--naranja)")}</div>
        </div>
        <div style="margin-top:12px"><h3>¿En qué distritos?</h3>${barras(datos.por_distrito.filter((d) => d.recojos).sort((a, b) => b.recojos - a.recojos).map((d) => [d.distrito, d.recojos]), "var(--verde)")}</div>
      </section>

      <section class="tarjeta" id="sigersol">
        <h2>SIGERSOL</h2>
        <p>El reporte anual de residuos de la municipalidad al MINAM. Desde aquí puede ir a reportar o revisar las cifras.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <a class="boton chico principal" href="${SIGERSOL}" target="_blank" rel="noopener">Ir a SIGERSOL Municipal</a>
          <a class="boton chico" href="${DATOS_ABIERTOS}" target="_blank" rel="noopener">Datos abiertos del Estado (buscar «SIGERSOL»)</a>
        </div>
      </section>

      <section class="tarjeta" id="inscritos">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
          <h2>Recicladores inscritos</h2>
          <label class="campo" style="flex-direction:row;align-items:center;gap:8px"><span>Buscar</span><input type="search" id="buscar" placeholder="Nombre o código" style="min-height:44px;width:220px"></label>
        </div>
        <div class="tabla-caja con-limite"><table>
          <thead><tr><th>Código</th><th>Nombre</th><th>DNI</th><th>Distrito</th><th>Recoge</th><th>Con</th><th>Capacitado</th><th>Fecha</th></tr></thead>
          <tbody id="filas"></tbody>
        </table></div>
      </section>
    </main>
  </div>
  <div class="velo" id="velo" hidden></div>`;

  // Menú lateral: baja hasta la sección (sin cambiar la dirección, que decide la pantalla)
  raiz.querySelectorAll("[data-ir]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    raiz.querySelector(`#${a.dataset.ir}`).scrollIntoView({ behavior: "smooth" });
  }));

  // Lista de recicladores con buscador
  const filas = raiz.querySelector("#filas");
  const pintarFilas = (texto = "") => {
    const t = texto.toLowerCase();
    filas.innerHTML = datos.lista.filter((f) => !t || `${f.nombre_completo} ${f.codigo}`.toLowerCase().includes(t)).map((f) => `
      <tr><td class="sin-corte"><strong>${esc(f.codigo)}</strong></td><td>${esc(f.nombre_completo)}</td><td class="sin-corte">${esc(f.dni)}</td><td>${esc(f.distrito_vivienda)}</td>
      <td>${esc(lista(f.materiales))}</td><td>${esc(lista(f.medio_transporte))}</td><td>${f.capacitado ? "Sí" : "No"}</td><td class="sin-corte">${fecha(f.fecha_registro)}</td></tr>`).join("");
  };
  pintarFilas();
  raiz.querySelector("#buscar").addEventListener("input", (e) => pintarFilas(e.target.value));

  // Filtro por distrito
  raiz.querySelectorAll("[data-distrito]").forEach((b) => b.addEventListener("click", () => {
    const d = b.dataset.distrito;
    elegidos.has(d) ? elegidos.delete(d) : elegidos.add(d);
    mapa?.remove();
    mostrar(raiz);
  }));

  // CSV de recicladores (el DNI ya viene oculto desde la API)
  raiz.querySelector("#csv").addEventListener("click", () => {
    const columnas = Object.keys(datos.lista[0] || {});
    const celda = (v) => `"${String(lista(v)).replace(/"/g, '""')}"`;
    const csv = [columnas.join(","), ...datos.lista.map((f) => columnas.map((c) => celda(f[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    a.download = "registro_recicladores.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  // Mapa: un círculo por distrito (más grande donde hay más recicladores) y los locales de acopio
  mapa = nuevoMapa(raiz.querySelector("#mapa"), [-8.09, -79.02], 12);
  datos.por_distrito.filter((d) => d.centro && d.recicladores).forEach((d) =>
    L.circleMarker(d.centro, { radius: 6 + Math.sqrt(d.recicladores) * 4, color: "#1E6B3C", fillOpacity: 0.35 })
      .bindTooltip(`${esc(d.distrito)}: ${d.recicladores} recicladores, ${d.vecinos} vecinos`).addTo(mapa));
  datos.acopios.forEach((a) => L.marker([a.lat, a.lon], { icon: pin("acopio", "S/") })
    .bindPopup(`<strong>${esc(a.nombre)}</strong><br>${esc(a.direccion)}`).addTo(mapa));

  // Resumen del mes: se ofrece al entrar y se puede abrir con el botón
  const velo = raiz.querySelector("#velo");
  const cerrar = () => { velo.hidden = true; velo.innerHTML = ""; };
  velo.addEventListener("click", (e) => { if (e.target === velo) cerrar(); });

  const elegirMes = (mes = datos.meses[0]) => `
    <label class="campo"><span>Mes</span><select id="mes">${datos.meses.map((m) => `<option value="${m}" ${m === mes ? "selected" : ""}>${nombreMes(m)}</option>`).join("")}</select></label>`;

  const ofrecer = () => {
    velo.hidden = false;
    velo.innerHTML = `
      <div class="ventana" role="dialog" aria-modal="true" aria-labelledby="titulo-mes">
        <h2 id="titulo-mes">¿Quiere ver el resumen del mes?</h2>
        <p class="subtitulo">Inscritos nuevos, recojos y kilos recogidos en el mes que elija.</p>
        ${elegirMes()}
        <div class="par">
          <button class="boton" type="button" id="otra-ocasion">En otra ocasión</button>
          <button class="boton principal" type="button" id="ver">Ver resumen</button>
        </div>
      </div>`;
    velo.querySelector("#otra-ocasion").addEventListener("click", cerrar);
    velo.querySelector("#ver").addEventListener("click", () => verResumen(velo.querySelector("#mes").value));
    velo.querySelector("#ver").focus();
  };

  const verResumen = async (mes) => {
    velo.hidden = false;
    velo.innerHTML = `<div class="ventana">${cargando("Calculando el resumen…")}</div>`;
    let r;
    try {
      r = await leer("/panel/mes", { mes, distritos: [...elegidos].join(",") });
    } catch (error) {
      velo.innerHTML = `<div class="ventana">${mensajeError(error)}<button class="boton" type="button" id="cerrar">Cerrar</button></div>`;
      velo.querySelector("#cerrar").addEventListener("click", cerrar);
      return;
    }
    // En el mes en curso no comparamos: todavía no termina.
    const cambio = r.recojos_recogidos_mes_anterior && !r.mes_en_curso
      ? Math.round(((r.recojos_recogidos - r.recojos_recogidos_mes_anterior) / r.recojos_recogidos_mes_anterior) * 100) : null;
    const filtro = elegidos.size ? ` · ${[...elegidos].join(", ")}` : "";
    velo.innerHTML = `
      <div class="ventana ancha" role="dialog" aria-modal="true" aria-labelledby="titulo-mes">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap">
          <div><span class="subtitulo">Resumen del mes${esc(filtro)}</span><h2 id="titulo-mes">${nombreMes(r.mes)}</h2></div>
          ${elegirMes(r.mes)}
        </div>
        <section class="indicadores">
          ${indicador("Recicladores nuevos", r.recicladores_nuevos)}
          ${indicador("Vecinos nuevos", r.vecinos_nuevos)}
          ${indicador("Acopios nuevos", r.acopios_nuevos)}
          ${indicador("Recojos pedidos", r.recojos_pedidos)}
          ${indicador(`Recojos hechos <span class="nota">(${r.mes_en_curso ? "mes en curso" : cambio === null ? "sin mes anterior" : `${cambio >= 0 ? "+" : ""}${cambio} % vs. mes anterior`})</span>`, r.recojos_recogidos)}
          ${indicador("Kilos recogidos", r.kg_recogidos.toLocaleString("es-PE"))}
          ${indicador("Recicladores que recogieron", r.recicladores_activos)}
          ${indicador("Días con recojo por reciclador (promedio)", r.dias_promedio_con_recojo.toLocaleString("es-PE"))}
        </section>
        <p>Horario más pedido: <strong>${esc(r.franja_mas_pedida || "—")}</strong> · Distrito con más recojos: <strong>${esc(r.distrito_con_mas_recojos || "—")}</strong></p>
        <p class="nota">Solo cuenta los recojos hechos con la app (cuando el reciclador marca «Ya lo recogí»).</p>
        <button class="boton principal" type="button" id="cerrar">Ver todo el panel</button>
      </div>`;
    velo.querySelector("#mes").addEventListener("change", (e) => verResumen(e.target.value));
    velo.querySelector("#cerrar").addEventListener("click", cerrar);
  };

  raiz.querySelector("#ver-mes").addEventListener("click", () => verResumen(datos.meses[0]));
  if (!yaOfrecido() && datos.meses.length) { marcarOfrecido(); ofrecer(); }

  return () => mapa?.remove();
}
