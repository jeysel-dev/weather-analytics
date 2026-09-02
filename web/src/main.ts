// Entrypoint do frontend (Vite + TypeScript), spec 006.
//
// Dispatch por página: `document.body.dataset.page` (definido no layout.html
// a partir da estrutura central de páginas em api/app/main.py) seleciona o
// módulo de render. Uma entrada por página migrada.

import { initHorario } from "./pages/horario";

const page = document.body.dataset.page;

if (page === "horario") {
  initHorario();
}
