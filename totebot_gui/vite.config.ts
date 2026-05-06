import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

export default defineConfig(({ mode }) => ({
  server: {
    host: "0.0.0.0", // Listens on all interfaces
    port: 8080,
    strictPort: true, 
    hmr: {
      // Removing 'host: "10.10.10.1"' allows the browser 
      // to resolve the HMR connection to whatever IP you are currently using.
      protocol: 'ws',
      clientPort: 8080,
      overlay: false, 
    },
    watch: {
      usePolling: true, 
    }
  },
  plugins: [
    react(), 
    mode === "development" && componentTagger()
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime"],
  },
  optimizeDeps: {
    rolldownOptions: {
      // Future-proofing for Vite 8/Rolldown
    }
  },
  build: {
    chunkSizeWarningLimit: 1000,
  }
}));