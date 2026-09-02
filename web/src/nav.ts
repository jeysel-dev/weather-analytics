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
