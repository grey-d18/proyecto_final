// Cómo habla la web con la API: pedir datos (GET) y mandar datos (POST/PUT).
import { API } from "./config.js";

async function pedir(ruta, opciones = {}) {
  let respuesta;
  try {
    respuesta = await fetch(API + ruta, opciones);
  } catch {
    throw new Error("No hay conexión con el servidor. Revise su internet; si sigue igual, puede que el servidor de prueba esté apagado.");
  }
  if (!respuesta.ok) {
    let mensaje = `El servidor respondió con un error (${respuesta.status}).`;
    try {
      const datos = await respuesta.json();
      if (typeof datos.detail === "string") mensaje = datos.detail;
    } catch { /* la respuesta no era JSON */ }
    throw new Error(mensaje);
  }
  return respuesta.json();
}

// Arma «?a=1&b=2» con los parámetros que tengan valor.
function consulta(parametros = {}) {
  const limpios = Object.entries(parametros).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return limpios.length ? "?" + new URLSearchParams(limpios).toString() : "";
}

export const leer = (ruta, parametros) => pedir(ruta + consulta(parametros));

export const enviar = (ruta, datos, metodo = "POST") =>
  pedir(ruta, { method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });

// Para archivos (audio, foto): se mandan como formulario.
export const enviarFormulario = (ruta, formulario) => pedir(ruta, { method: "POST", body: formulario });

// Direcciones que el navegador abre directamente (PDF, fotos).
export const enlace = (ruta) => API + ruta;
