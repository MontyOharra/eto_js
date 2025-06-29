import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: "./",
  root: "src/app",
  build: {
    outDir: "../../build/dist-react",
  },
  server: {
    port: 5000,
    strictPort: true,
  },
});
