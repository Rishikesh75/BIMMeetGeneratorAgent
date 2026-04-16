import { Router, type IRouter } from "express";
import healthRouter from "./health.js";
import bimRouter from "./bim/index.js";

const router: IRouter = Router();

router.get("/", (_req, res) => {
  res.type("html").send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BIM Meet Generator API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #111; }
    h1 { font-size: 1.25rem; border-bottom: 1px solid #ddd; padding-bottom: 0.5rem; }
    ul { padding-left: 1.25rem; }
    code { background: #f4f4f5; padding: 0.1em 0.35em; border-radius: 4px; font-size: 0.9em; }
    a { color: #2563eb; }
    p.muted { color: #666; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>BIM Meet Generator API</h1>
  <p class="muted">This service exposes JSON under <code>/api</code>. There is no Swagger UI in this build; the contract lives in <code>lib/api-spec/openapi.yaml</code> in the repo.</p>
  <p><strong>Quick links</strong></p>
  <ul>
    <li><a href="/api/healthz"><code>GET /api/healthz</code></a> — health check</li>
    <li><code>POST /api/bim/generate</code> — start BIM job (JSON body)</li>
    <li><a href="/api/bim/jobs"><code>GET /api/bim/jobs</code></a> — list jobs</li>
    <li><code>GET /api/bim/jobs/:jobId</code> — job status</li>
    <li><code>GET /api/bim/jobs/:jobId/download</code> — download <code>.ifc</code> when complete</li>
  </ul>
</body>
</html>`);
});

router.use(healthRouter);
router.use("/bim", bimRouter);

export default router;
