// La grabadora del registro.
//
// Abre el micrófono UNA vez (al apretar «Empezar») y lo deja abierto hasta salir del registro:
//   - el navegador pide permiso una sola vez, no en cada pregunta;
//   - al apretar el micrófono la grabación empieza al instante: no se pierde la primera sílaba.
// Mientras graba, mide el volumen para mover la onda y para DETENERSE SOLA cuando la persona
// deja de hablar (también se detiene si se vuelve a apretar).
//
// Para no cortar a quien hace pausas o habla bajito:
//   - espera 3,5 segundos de silencio, y avisa con una cuenta regresiva antes de cortar;
//   - mide el ruido del lugar al empezar: cuenta como voz lo que esté claramente por encima.

const SILENCIO_PARA_PARAR = 3500; // milisegundos de silencio, después de haber hablado
const AVISAR_DESDE = 500;         // a partir de este silencio se muestra la cuenta regresiva
const MAXIMO_POR_DEFECTO = 30;    // segundos; cada pregunta puede pedir más (ver nucleo/preguntas.py)
const CALIBRAR = 400;             // milisegundos del inicio en que se mide el ruido del lugar
const UMBRAL_MINIMO = 0.012;      // volumen desde el que contamos que hay voz (0 a 1)…
const UMBRAL_MAXIMO = 0.04;       // …ajustado al ruido del lugar, entre estos dos valores

let flujo = null;
let contexto = null;
let analizador = null;

export async function abrirMicrofono() {
  if (flujo) return;
  flujo = await navigator.mediaDevices.getUserMedia({
    // Sin cancelación de eco ni supresión de ruido: están hechas para llamadas y deforman la voz
    // que Whisper necesita entender (Whisper ya está entrenado con audios con ruido).
    audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true },
  });
  contexto = new (window.AudioContext || window.webkitAudioContext)();
  analizador = contexto.createAnalyser();
  analizador.fftSize = 1024;
  contexto.createMediaStreamSource(flujo).connect(analizador);
}

export function cerrarMicrofono() {
  flujo?.getTracks().forEach((pista) => pista.stop());
  contexto?.close().catch(() => {});
  flujo = contexto = analizador = null;
}

export const microfonoAbierto = () => flujo !== null;

// Chrome y Android graban en WebM; Safari y el iPhone en MP4. Whisper entiende los dos.
function formato() {
  for (const tipo of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]) {
    if (window.MediaRecorder?.isTypeSupported?.(tipo)) return tipo;
  }
  return "";
}

function volumen() {
  const muestras = new Float32Array(analizador.fftSize);
  analizador.getFloatTimeDomainData(muestras);
  let suma = 0;
  for (const m of muestras) suma += m * m;
  return Math.sqrt(suma / muestras.length);
}

// Empieza a grabar.
//   alCambiarVolumen(v): se llama muchas veces por segundo (para la onda).
//   alContar(n): n = segundos que faltan para cortar por silencio (3, 2, 1), o null si la persona habla.
//   segundos: lo máximo que puede durar la respuesta.
// Devuelve { detener(), terminado }: «terminado» es una promesa con el audio (Blob) y su extensión.
export function grabar({ alCambiarVolumen = () => {}, alContar = () => {}, segundos = MAXIMO_POR_DEFECTO } = {}) {
  if (contexto?.state === "suspended") contexto.resume();
  const tipo = formato();
  const grabadora = new MediaRecorder(flujo, tipo ? { mimeType: tipo } : undefined);
  const pedazos = [];
  grabadora.ondataavailable = (e) => e.data.size && pedazos.push(e.data);

  let hablo = false;
  let ultimoSonido = performance.now();
  const inicio = performance.now();
  let reloj = 0;
  let ruido = Infinity;        // el volumen más bajo del inicio: el ruido de fondo del lugar
  let umbral = UMBRAL_MINIMO;
  let cuentaAnterior = null;

  const terminado = new Promise((resolver) => {
    grabadora.onstop = () => {
      cancelAnimationFrame(reloj);
      const tipoFinal = grabadora.mimeType || tipo || "audio/webm";
      resolver({ audio: new Blob(pedazos, { type: tipoFinal }), extension: tipoFinal.includes("mp4") ? ".mp4" : ".webm" });
    };
  });

  const detener = () => { if (grabadora.state === "recording") grabadora.stop(); };

  const vigilar = () => {
    const v = volumen();
    alCambiarVolumen(v);
    const ahora = performance.now();
    if (ahora - inicio < CALIBRAR) {
      // Usamos el momento más silencioso (no el promedio): si la persona empieza a hablar
      // enseguida, su voz no sube el umbral.
      ruido = Math.min(ruido, v);
      umbral = Math.min(UMBRAL_MAXIMO, Math.max(UMBRAL_MINIMO, ruido * 3));
    }
    if (v > umbral) { hablo = true; ultimoSonido = ahora; }

    const silencio = ahora - ultimoSonido;
    const cuenta = hablo && silencio > AVISAR_DESDE ? Math.ceil((SILENCIO_PARA_PARAR - silencio) / 1000) : null;
    if (cuenta !== cuentaAnterior) { cuentaAnterior = cuenta; alContar(cuenta); }

    if ((hablo && silencio > SILENCIO_PARA_PARAR) || ahora - inicio > segundos * 1000) return detener();
    reloj = requestAnimationFrame(vigilar);
  };

  grabadora.start();
  reloj = requestAnimationFrame(vigilar);
  return { detener, terminado };
}
