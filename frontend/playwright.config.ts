import { defineConfig } from "@playwright/test";

// Hermetic e2e: stub LLM, no Supabase (backend runs with AUTH_REQUIRED=false), separate ports.
const API = "http://localhost:8100";
const WEB = "http://localhost:3100";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1, // tests share one backend and one guest user; privacy.spec deletes all of that user's data
  reporter: [["list"]],
  use: {
    baseURL: WEB,
    trace: "off",
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
  webServer: [
    {
      command: "uv run fastapi run app/main.py --port 8100",
      cwd: "../backend",
      url: `${API}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        GEMINI_API_KEY: "",
        SUPABASE_URL: "",
        SUPABASE_SECRET_KEY: "",
        AUTH_REQUIRED: "false",
        CORS_ORIGINS: JSON.stringify([WEB]),
      },
    },
    {
      command: "pnpm exec next dev -p 3100",
      url: WEB,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_URL: API,
        NEXT_PUBLIC_SUPABASE_URL: "",
        NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "",
      },
    },
  ],
});
