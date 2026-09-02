import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  // Servido sob /static/api/ (spec 090): o Ingress roteia esse prefixo para a
  // API; /static/ puro é namespace do bundle do Streamlit durante a coexistência.
  base: "/static/api/",
  build: {
    outDir: "../api/app/static",
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: resolve(import.meta.dirname, "src/main.ts"),
    },
  },
});
