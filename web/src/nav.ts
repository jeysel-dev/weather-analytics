export function initNavbarToggle(): void {
  const toggle = document.getElementById("navbar-toggle");
  const links = document.getElementById("navbar-links");
  if (toggle === null || links === null) return;

  const closeMenu = () => {
    links.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
  };
  const openMenu = () => {
    links.classList.add("open");
    toggle.setAttribute("aria-expanded", "true");
  };

  toggle.addEventListener("click", () => {
    if (links.classList.contains("open")) closeMenu(); else openMenu();
  });
  links.addEventListener("click", (event) => {
    if ((event.target as HTMLElement).closest("a") !== null) closeMenu();
  });
  document.addEventListener("click", (event) => {
    if (!links.classList.contains("open")) return;
    const target = event.target as Node;
    if (!links.contains(target) && !toggle.contains(target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && links.classList.contains("open")) {
      closeMenu();
      toggle.focus();
    }
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 720) closeMenu();
  });
}

// Submenu da navbar ("Relatórios", spec 017). CSS-only não serve: aria-expanded
// tem que refletir o estado real e o toque no mobile precisa de clique, não
// :hover. Cada toggle abre/fecha sua própria lista; clique fora e Esc fecham.
export function initNavSubmenu(): void {
  const toggles = document.querySelectorAll<HTMLButtonElement>(".site-nav__sub-toggle");
  for (const toggle of toggles) {
    const item = toggle.closest(".site-nav__has-sub");
    if (item === null) continue;

    const close = () => toggle.setAttribute("aria-expanded", "false");
    const isOpen = () => toggle.getAttribute("aria-expanded") === "true";

    toggle.addEventListener("click", () => {
      toggle.setAttribute("aria-expanded", isOpen() ? "false" : "true");
    });
    document.addEventListener("click", (event) => {
      if (isOpen() && !item.contains(event.target as Node)) close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && isOpen()) {
        close();
        toggle.focus();
      }
    });
  }
}
