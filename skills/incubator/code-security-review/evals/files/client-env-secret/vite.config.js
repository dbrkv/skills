import { defineConfig } from 'vite';

// Expose the build-time secret to the client bundle.
export default defineConfig({
  define: {
    'process.env.STRIPE_SECRET_KEY': JSON.stringify(process.env.STRIPE_SECRET_KEY),
  },
});
