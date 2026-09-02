// Entrypoint do frontend (Vite + TypeScript), spec 006.
//
// O dispatch por página (`document.body.dataset.page` → função de render de
// cada gráfico) entra a partir da spec 010, junto com a primeira página
// migrada. Por enquanto só existe para o build do Vite gerar o manifest que
// o backend lê em nível de módulo (`_load_main_entry` em api/app/main.py).
console.log("weather-analytics: bundle do frontend carregado");
