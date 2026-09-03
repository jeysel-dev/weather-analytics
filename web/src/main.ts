// Entrypoint do frontend (Vite + TypeScript), spec 006.
//
// Dispatch por página: `document.body.dataset.page` (definido no layout.html
// a partir da estrutura central de páginas em api/app/main.py) seleciona o
// módulo de render. Uma entrada por página migrada.

// CSS base do Tom Select ANTES do nosso style.css: a re-tematização (tokens
// --bg-card/--border/--accent/…) vive em style.css e precisa vencer a
// cascata. Ver web/src/citypicker.ts e spec 020.
import "tom-select/dist/css/tom-select.css";
import "./style.css";

import { initNavSubmenu, initNavbarToggle } from "./nav";
import { initAlertas } from "./pages/alertas";
import { initCidades } from "./pages/cidades";
import { initComparativo } from "./pages/comparativo";
import { initHome } from "./pages/home";
import { initHorario } from "./pages/horario";
import { initPrecipitacao } from "./pages/precipitacao";
import { initRelatorioChuvaAcumulada } from "./pages/relatorio-chuva-acumulada";
import { initRelatorioCidade } from "./pages/relatorio-cidade";
import { initRelatorioExtremos } from "./pages/relatorio-extremos";
import { initRelatorioHorario } from "./pages/relatorio-horario";
import { initRelatorioMacrorregiao } from "./pages/relatorio-macrorregiao";
import { initRelatorioMensal } from "./pages/relatorio-mensal";
import { initTemperatura } from "./pages/temperatura";

const page = document.body.dataset.page;

const DISPATCH: Record<string, () => void> = {
  home: initHome,
  temperatura: initTemperatura,
  precipitacao: initPrecipitacao,
  alertas: initAlertas,
  horario: initHorario,
  cidades: initCidades,
  comparativo: initComparativo,
  "relatorio-cidade": initRelatorioCidade,
  "relatorio-mensal": initRelatorioMensal,
  "relatorio-macrorregiao": initRelatorioMacrorregiao,
  "relatorio-extremos": initRelatorioExtremos,
  "relatorio-chuva-acumulada": initRelatorioChuvaAcumulada,
  "relatorio-horario": initRelatorioHorario,
};

// Roda em toda página (o toggle só faz algo onde o CSS mostra o hambúrguer).
initNavbarToggle();
initNavSubmenu();

if (page !== undefined && page in DISPATCH) {
  DISPATCH[page]();
}
