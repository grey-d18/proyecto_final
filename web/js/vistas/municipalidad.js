// Panel municipal: indicadores, gráficos, mapa, comparación con SIGERSOL y la lista de inscritos.
import { leer } from "../api.js";
import { cargando, esc, icono, logo, mensajeError, nuevoMapa } from "../comun.js";

const elegidos = new Set(); // distritos del filtro (vacío = todos)

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
  const maxDistrito = Math.max(1, ...datos.por_distrito.map((d) => d.inscritos));
  const maxMaterial = Math.max(1, ...datos.materiales.map((m) => m.personas));
  const barras = (filas, max, color) => `<div class="barras" style="--c:${color}">${filas.map(([nombre, n]) => `
    <span>${esc(nombre)}</span><div class="barra-dato" style="width:${(n / max) * 100}%"></div><span class="numero">${n}</span>`).join("")}</div>`;
  const lista = (v) => (Array.isArray(v) ? v.join(", ") : v ?? "");

  raiz.innerHTML = `
  <div class="panel">
    <aside>
      <a class="marca" href="#/" style="color:#FFFFFF;padding:0">${logo}<span style="display:flex;flex-direction:column;line-height:1.2">ReciclaVoz<span style="font-size:13px;font-weight:400;color:#B8C4BC">Municipalidad de Trujillo</span></span></a>
      <nav aria-label="Panel">
        <a href="#/municipalidad" data-ir="resumen">Resumen</a><a href="#/municipalidad" data-ir="mapa-panel">Mapa</a><a href="#/municipalidad" data-ir="sigersol">SIGERSOL</a><a href="#/municipalidad" data-ir="inscritos">Inscritos</a><a href="#/">Salir</a>
      </nav>
    </aside>
    <main>
      <header id="resumen" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap">
        <div><h1>Registro de recicladores</h1><p class="subtitulo">Provincia de Trujillo · datos sintéticos + registros hechos en el demo</p></div>
        <button class="boton chico principal" type="button" id="csv">${icono("descargar", 18)} Descargar CSV</button>
      </header>
      <div class="chips" aria-label="Filtrar por distrito">
        ${datos.todos_los_distritos.map((d) => `<button type="button" class="chip" aria-pressed="${elegidos.has(d)}" data-distrito="${esc(d)}">${esc(d)}</button>`).join("")}
      </div>
      <section class="indicadores" aria-label="Indicadores">
        <div class="indicador"><span class="nombre">Inscritos</span><span class="valor">${k.inscritos}</span></div>
        <div class="indicador"><span class="nombre">En una asociación</span><span class="valor">${k.en_asociacion} %</span></div>
        <div class="indicador"><span class="nombre">Capacitados</span><span class="valor">${k.capacitados} %</span></div>
        <div class="indicador"><span class="nombre">Sin guantes</span><span class="valor">${k.sin_guantes} %</span></div>
        <div class="indicador alerta"><span class="nombre">Solo con saco (necesitan equipo)</span><span class="valor">${k.solo_saco}</span></div>
      </section>
      <section class="dos-columnas">
        <div class="tarjeta"><h2>Dónde viven</h2>${barras(datos.por_distrito.map((d) => [d.distrito, d.inscritos]), maxDistrito, "var(--verde)")}</div>
        <div class="tarjeta"><h2>Qué recogen <span class="nota">(personas)</span></h2>${barras(datos.materiales.map((m) => [m.material, m.personas]), maxMaterial, "var(--azul)")}</div>
      </section>
      <section class="tarjeta" id="mapa-panel"><h2>¿Dónde viven los recicladores inscritos?</h2><div class="mapa alto" id="mapa"></div></section>
      <section class="tarjeta" id="sigersol">
        <h2>Inscritos frente a lo que reporta el distrito (${datos.anio_sigersol})</h2>
        <div class="tabla-caja"><table>
          <thead><tr><th>Distrito</th><th>Inscritos</th><th>Valorizado oficial (t)</th><th>Residuos generados (t)</th><th>% reciclado oficial</th></tr></thead>
          <tbody>${datos.por_distrito.map((d) => `<tr><td>${esc(d.distrito)}</td><td>${d.inscritos}</td>
            <td>${d.valorizado_t?.toLocaleString("es-PE") ?? "—"}</td><td>${d.generado_t?.toLocaleString("es-PE") ?? "—"}</td><td>${d.pct_valorizado ?? "—"}</td></tr>`).join("")}</tbody>
        </table></div>
        <p class="nota">SIGERSOL (MINAM), datos abiertos por distrito. Lo que recogen los recicladores informales casi no aparece en las cifras oficiales: el registro es el primer paso para contarlo.</p>
      </section>
      <section class="tarjeta" id="inscritos">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
          <h2>Inscritos</h2>
          <label class="campo" style="flex-direction:row;align-items:center;gap:8px"><span>Buscar</span><input type="search" id="buscar" placeholder="Nombre o código" style="min-height:44px;width:220px"></label>
        </div>
        <div class="tabla-caja con-limite"><table>
          <thead><tr><th>Código</th><th>Nombre</th><th>DNI</th><th>Distrito</th><th>Recoge</th><th>Con</th><th>Capacitado</th><th>Fecha</th></tr></thead>
          <tbody id="filas"></tbody>
        </table></div>
      </section>
    </main>
  </div>`;

  // Menú lateral: baja hasta la sección (sin cambiar la dirección, que decide la pantalla)
  raiz.querySelectorAll("[data-ir]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    raiz.querySelector(`#${a.dataset.ir}`).scrollIntoView({ behavior: "smooth" });
  }));

  // Lista con buscador
  const filas = raiz.querySelector("#filas");
  const pintarFilas = (texto = "") => {
    const t = texto.toLowerCase();
    filas.innerHTML = datos.lista.filter((f) => !t || `${f.nombre_completo} ${f.codigo}`.toLowerCase().includes(t)).map((f) => `
      <tr><td class="sin-corte"><strong>${esc(f.codigo)}</strong></td><td>${esc(f.nombre_completo)}</td><td class="sin-corte">${esc(f.dni)}</td><td>${esc(f.distrito_vivienda)}</td>
      <td>${esc(lista(f.materiales))}</td><td>${esc(lista(f.medio_transporte))}</td><td>${f.capacitado ? "Sí" : "No"}</td><td class="sin-corte">${esc((f.fecha_registro || "").slice(0, 10))}</td></tr>`).join("");
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

  // CSV (el DNI ya viene oculto desde la API)
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

  // Mapa: un círculo por distrito, más grande donde hay más inscritos
  mapa = nuevoMapa(raiz.querySelector("#mapa"), [-8.09, -79.02], 12);
  datos.por_distrito.filter((d) => d.centro).forEach((d) =>
    L.circleMarker(d.centro, { radius: 6 + Math.sqrt(d.inscritos) * 4, color: "#1E6B3C", fillOpacity: 0.45 })
      .bindTooltip(`${esc(d.distrito)}: ${d.inscritos} inscritos`).addTo(mapa));
  return () => mapa?.remove();
}
