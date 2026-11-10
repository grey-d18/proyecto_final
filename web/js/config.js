// Dónde está la API (la carpeta api/ del proyecto).
// En tu laptop: la API corre en el puerto 8000 (ver README, «Cómo correrlo»).
// En internet: la dirección del Space de Hugging Face donde se publicó la API.
const enMiLaptop = ["localhost", "127.0.0.1"].includes(location.hostname);

export const API = enMiLaptop
  ? `http://${location.hostname}:8000`
  : "https://COMPLETAR-usuario-reciclavoz-api.hf.space"; // [COMPLETAR] al publicar la API
