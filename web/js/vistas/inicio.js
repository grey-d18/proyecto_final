// Inicio: «¿Quién es usted?». En el celular, tarjetas grandes; en la computadora, portada.
import { hablar, icono, logo } from "../comun.js";

export function mostrar(raiz) {
  const opcion = (ruta, titulo, detalle, ico, principal = false) => `
    <a class="opcion ${principal ? "principal" : ""}" href="#/${ruta}">
      <span class="icono" style="color:${principal ? "#FFFFFF" : "var(--verde)"}">${icono(ico, 30, 1.8)}</span>
      <span class="textos"><span class="titulo">${titulo}</span><span class="detalle">${detalle}</span></span>
      ${icono("adelante", 24)}
    </a>`;

  const paso = (n, titulo, texto) => `
    <div class="tarjeta"><span class="chip" style="align-self:flex-start">${n}</span><h3>${titulo}</h3><p class="subtitulo">${texto}</p></div>`;

  raiz.innerHTML = `
  <div class="pantalla inicio">
    <header class="barra">
      <a class="marca" href="#/">${logo}EcoBarrio</a>
      <button class="boton-redondo" type="button" id="escuchar" aria-label="Escuchar esta pantalla">${icono("parlante", 22)}</button>
    </header>

    <section class="portada">
      <div class="lado">
        <div style="display:flex;flex-direction:column;gap:8px">
          <h1>¿Quién es usted?</h1>
          <p class="subtitulo">Toque una opción. Inscríbase hablando, sin papeles.</p>
        </div>
        <nav class="opciones" aria-label="Elegir rol">
          ${opcion("reciclador", "Soy reciclador", "Inscribirme, mi ruta, recojos", "carrito", true)}
          ${opcion("vecino", "Soy vecino", "Tengo reciclaje para que lo recojan", "casa")}
          ${opcion("acopiador", "Soy acopiador", "Mis precios del día y mi local", "tienda")}
        </nav>
      </div>
      <div class="muestra" aria-hidden="true">
        <div class="telefono"><div class="dentro">
          <span class="nota" style="text-align:center;font-weight:700">Pregunta 1 de 6</span>
          <div class="tarjeta" style="padding:16px"><strong style="font-size:22px;line-height:1.2">¿Cuál es su número de DNI?</strong></div>
          <div class="zona-micro" style="min-height:0">
            <span class="micro" style="width:112px;height:112px;border-width:8px;color:#FFFFFF">${icono("micro", 46, 1.8)}</span>
            <strong>Toque para hablar</strong>
          </div>
        </div></div>
      </div>
    </section>

    <section class="pasos-portada" aria-label="Cómo funciona">
      ${paso(1, "Escucha y responde", "Cada pregunta se escucha en voz alta. La persona responde hablando, sin escribir.")}
      ${paso(2, "La IA llena la ficha", "Whisper convierte la voz en texto y Gemini ordena las respuestas en la ficha del registro.")}
      ${paso(3, "Constancia y panel", "La persona recibe su constancia en PDF y la municipalidad ve el registro en su panel.")}
    </section>

    <div class="empuja"></div>
    <footer style="display:flex;flex-direction:column;align-items:center;gap:6px;text-align:center">
      <a href="#/municipalidad" style="font-weight:700;padding:12px">Soy de la municipalidad</a>
      <span class="nota">Registro Municipal de Recicladores · Trujillo · Ley 29419</span>
    </footer>
  </div>`;

  raiz.querySelector("#escuchar").addEventListener("click", () => hablar("inicio"));
}
