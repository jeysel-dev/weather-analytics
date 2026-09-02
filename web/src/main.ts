// Entrypoint do frontend (Vite + TypeScript), spec 006.
//
// Dispatch por página: `document.body.dataset.page` (definido no layout.html
// a partir da estrutura central de páginas em api/app/main.py) seleciona o
// módulo de render. Uma entrada por página migrada.

import { initAlertas } from "./pages/alertas";
import { initCidades } from "./pages/cidades";
import { initComparativo } from "./pages/comparativo";
import { initHorario } from "./pages/horario";
import { initPrecipitacao } from "./pages/precipitacao";
import { initRelatorioCidade } from "./pages/relatorio-cidade";
import { initTemperatura } from "./pages/temperatura";

const page = document.body.dataset.page;

const DISPATCH: Record<string, () => void> = {
  temperatura: initTemperatura,
  precipitacao: initPrecipitacao,
  alertas: initAlertas,
  horario: initHorario,
  cidades: initCidades,
  comparativo: initComparativo,
  "relatorio-cidade": initRelatorioCidade,
};

if (page !== undefined && page in DISPATCH) {
  DISPATCH[page]();
}
