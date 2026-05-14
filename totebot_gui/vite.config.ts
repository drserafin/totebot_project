import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

export default defineConfig(({ mode }) => ({
  server: {
    host: "0.0.0.0", 
    port: 8080,
    strictPort: true, 
    hmr: {
      // Forcing the protocol to 'ws' and ensuring the clientPort matches
      // helps bypass the "RSV1 must be clear" error caused by proxies.
      protocol: 'ws',
      clientPort: 8080,
      overlay: false, 
    },
    watch: {
      usePolling: true, 
      interval: 100, // Added a slight interval to save Pi CPU cycles
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
    // Consolidating dependencies to prevent version mismatch
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime"],
  },
  // Fixed the deprecation warning by ensuring we use rolldownOptions
  optimizeDeps: {
    rolldownOptions: {
      // Configuration for Vite 8's new bundler
    }
  },
  build: {
    chunkSizeWarningLimit: 1000,
  }
}));