// Compartilhar no WhatsApp + estado dos filtros na URL — compartilhado
// pelas páginas de relatório (spec 024).
//
// Cada página lê os filtros da query string ao abrir (`lerURL`) e reescreve
// a cada mudança (`escreverURL`); quando há um resultado, chama
// `compartilharWhatsapp` para montar o link wa.me/ no #btn-compartilhar
// (markup em api/app/templates/_share_button.html).

const DOMINIO_PUBLICO = "https://weather.jeysel.dev";

export function lerURL(): URLSearchParams {
  return new URLSearchParams(window.location.search);
}

export function escreverURL(params: URLSearchParams): void {
  const qs = params.toString();
  window.history.replaceState(null, "", qs === "" ? window.location.pathname : `?${qs}`);
}

/** Monta `https://wa.me/?text=…` no #btn-compartilhar e o revela. `resumo` é
 *  a 1ª linha da mensagem; a URL pública do relatório (domínio + caminho
 *  atual + `params`) entra na 2ª. */
export function compartilharWhatsapp(resumo: string, params: URLSearchParams): void {
  const botao = document.getElementById("btn-compartilhar") as HTMLAnchorElement | null;
  if (botao === null) return;
  const qs = params.toString();
  const url = `${DOMINIO_PUBLICO}${window.location.pathname}${qs === "" ? "" : `?${qs}`}`;
  const msg = `${resumo}\nVeja o relatório completo: ${url}`;
  botao.href = `https://wa.me/?text=${encodeURIComponent(msg)}`;
  botao.hidden = false;
}

export function esconderCompartilhar(): void {
  const botao = document.getElementById("btn-compartilhar");
  if (botao !== null) botao.hidden = true;
}
