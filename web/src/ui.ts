// Helpers de DOM + ECharts compartilhados pelos módulos de página da
// migração (spec 006). `web/src/pages/horario.ts` (a 1ª página migrada)
// mantém cópias locais destes helpers — as páginas seguintes (007–013)
// importam daqui para não repetir ~40 linhas de boilerplate por arquivo.

import * as echarts from "echarts";

export function byId<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

export function toggle(node: HTMLElement | null, visible: boolean): void {
  if (node !== null) node.hidden = !visible;
}

export function toggleId(id: string, visible: boolean): void {
  toggle(byId(id), visible);
}

export function setText(id: string, text: string): void {
  const node = byId(id);
  if (node !== null) {
    node.hidden = false;
    node.textContent = text;
  }
}

const resizeBound = new Set<string>();

export function chartFor(id: string): echarts.ECharts | null {
  const container = document.getElementById(id);
  if (container === null) return null;
  const chart = echarts.getInstanceByDom(container) ?? echarts.init(container);
  requestAnimationFrame(() => chart.resize());
  if (!resizeBound.has(id)) {
    resizeBound.add(id);
    window.addEventListener("resize", () => chart.resize());
  }
  return chart;
}

export function clearChart(id: string): void {
  const container = document.getElementById(id);
  if (container === null) return;
  echarts.getInstanceByDom(container)?.clear();
}

// Abas acessíveis: botões `.tab-btn[data-tab]` + painéis `#tab-<nome>`.
// Mesmo comportamento do initTabs local de horario.ts, generalizado.
export function initTabs(onShow?: (name: string) => void): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".tab-btn"));
  const names = buttons.map((b) => b.dataset.tab).filter((n): n is string => n !== undefined);
  for (const btn of buttons) {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      if (target === undefined) return;
      for (const other of buttons) other.setAttribute("aria-selected", String(other === btn));
      for (const name of names) toggleId(`tab-${name}`, name === target);
      if (onShow !== undefined) onShow(target);
    });
  }
}
