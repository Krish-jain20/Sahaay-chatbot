# Temporary public demo link (Windows, PowerShell)

For a short demo only. Not a production deployment.

1. Install the tunnel tool once: `winget install Cloudflare.cloudflared` (then reopen PowerShell).
2. Backend (window 1): `cd backend; uv run uvicorn app.main:app --port 8001`
3. Frontend (window 2), built so the browser calls `/api` on the same link:
   ```
   cd frontend
   $env:BACKEND_URL="http://127.0.0.1:8001"; $env:NEXT_PUBLIC_API_URL="/api"
   pnpm build; pnpm start
   ```
4. Tunnel (window 3): `cloudflared tunnel --url http://localhost:3000`. Share the `https://...trycloudflare.com` link it prints.
5. Stop: Ctrl+C in each window. The link dies with the tunnel.

Notes: keep keys in `.env` only. Visitors use your Gemini/Tavily quota. With `AUTH_REQUIRED=false` all visitors share one user, so keep the link short-lived.
