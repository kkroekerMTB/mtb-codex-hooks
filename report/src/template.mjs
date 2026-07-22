export function renderHtml(reportData, browserBundle) {
  const serializedData = JSON.stringify(reportData).replaceAll("<", "\\u003c");
  const safeBundle = browserBundle.replaceAll("</script", "<\\/script");
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Codex Hooks Usage Report</title>
  <style>${styles}</style>
</head>
<body>
  <main>
    <header>
      <p class="eyebrow">Codex hooks analytics</p>
      <h1>AI usage report</h1>
      <p>Generated ${escapeHtml(reportData.generatedAt)} from normalized hook CSV data.</p>
    </header>

    <section class="summary" aria-label="Usage summary">
      ${card("API-equivalent cost", "cost")}
      ${card("Total tokens", "tokens")}
      ${card("Cache hit rate", "cache")}
      ${card("Model calls", "calls")}
      ${card("Sessions", "sessions")}
    </section>

    <p class="warning" data-unpriced-models hidden></p>

    <section class="panel wide">
      <div class="panel-heading">
        <h2>Token usage over time</h2>
        <p>Daily model-call tokens, split into non-overlapping categories.</p>
      </div>
      <div class="chart chart-wide"><canvas id="token-timeline"></canvas></div>
    </section>

    <section class="grid">
      <article class="panel">
        <div class="panel-heading">
          <h2>Usage by model and reasoning level</h2>
          <p>Token share; hover for estimated cost.</p>
        </div>
        <div class="chart"><canvas id="model-reasoning"></canvas></div>
      </article>
      <article class="panel">
        <div class="panel-heading">
          <h2>Skills invoked</h2>
          <p>Inferred from skill paths found in tool inputs.</p>
        </div>
        <div class="chart"><canvas id="skills"></canvas></div>
      </article>
    </section>

    <section class="panel wide">
      <div class="panel-heading">
        <h2>Tool calls</h2>
        <p>One count per logical call, grouped by <code>tool_name</code>.</p>
      </div>
      <div class="chart chart-tools"><canvas id="tools"></canvas></div>
    </section>

    <footer>
      <strong>Cost assumption:</strong> ${escapeHtml(reportData.pricing.name)}, effective
      ${escapeHtml(reportData.pricing.effectiveDate)}, per ${reportData.pricing.unitTokens.toLocaleString()} tokens.
      This is a directional API-equivalent estimate, not an invoice or a measurement of included Codex subscription usage.
      <a href="${escapeHtml(reportData.pricing.source)}">Pricing source</a>.
    </footer>
  </main>
  <script>window.__CODEX_HOOKS_REPORT__=${serializedData};</script>
  <script>${safeBundle}</script>
</body>
</html>`;
}

function card(label, value) {
  return `<article class="summary-card"><span>${label}</span><strong data-value="${value}">—</strong></article>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const styles = `
:root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #172033; background: #eef2f7; }
* { box-sizing: border-box; }
body { margin: 0; background: radial-gradient(circle at top left, #dbeafe 0, transparent 34rem), #eef2f7; }
main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0 32px; }
header { margin-bottom: 28px; }
h1, h2, p { margin-top: 0; }
h1 { margin-bottom: 8px; font-size: clamp(2rem, 5vw, 3.4rem); letter-spacing: -0.045em; }
h2 { margin-bottom: 6px; font-size: 1.1rem; }
p { color: #596579; }
.eyebrow { margin-bottom: 8px; color: #2563eb; font-size: .75rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
.summary { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.summary-card, .panel { border: 1px solid #d9e0ea; border-radius: 16px; background: rgba(255,255,255,.94); box-shadow: 0 12px 32px rgba(37,50,75,.07); }
.summary-card { padding: 18px; }
.summary-card span { display: block; margin-bottom: 8px; color: #6b7280; font-size: .78rem; }
.summary-card strong { font-size: clamp(1.25rem, 3vw, 1.8rem); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 18px 0; }
.panel { padding: 20px; min-width: 0; }
.panel-heading p { margin-bottom: 0; font-size: .86rem; }
.wide { margin-top: 18px; }
.chart { position: relative; height: 340px; margin-top: 20px; }
.chart-wide { height: 390px; }
.chart-tools { min-height: 340px; height: min(650px, max(340px, 45vw)); }
.warning { padding: 12px 16px; border: 1px solid #fdba74; border-radius: 12px; color: #9a3412; background: #fff7ed; }
footer { margin-top: 20px; color: #657186; font-size: .8rem; line-height: 1.6; }
a { color: #2563eb; }
code { padding: 2px 5px; border-radius: 5px; background: #eef2f7; }
@media (max-width: 800px) { .summary { grid-template-columns: repeat(2, 1fr); } .grid { grid-template-columns: 1fr; } main { padding-top: 28px; } }
@media print { body { background: #fff; } main { width: 100%; padding: 0; } .panel, .summary-card { box-shadow: none; break-inside: avoid; } }
`;
