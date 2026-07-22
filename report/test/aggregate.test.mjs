import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { buildReportData, estimateModelCallCost } from "../src/aggregate.mjs";

const pricing = JSON.parse(
  await readFile(new URL("../pricing/openai-api.json", import.meta.url), "utf8"),
);

test("estimates model-call cost without double-counting cached token categories", () => {
  const cost = estimateModelCallCost(
    {
      model: "gpt-5.6-sol",
      uncached_input_tokens: "300",
      cached_input_tokens: "600",
      cache_write_input_tokens: "100",
      output_tokens: "250",
    },
    pricing,
  );

  assert.equal(cost, 0.009925);
});

test("uses long-context pricing when a model call exceeds the configured threshold", () => {
  const cost = estimateModelCallCost(
    {
      model: "gpt-5.6-sol",
      input_tokens: "300000",
      uncached_input_tokens: "300000",
      cached_input_tokens: "0",
      cache_write_input_tokens: "0",
      output_tokens: "100",
    },
    pricing,
  );

  assert.equal(cost, 3.0045);
});

test("builds chart-ready token, model, skill, and tool summaries", () => {
  const report = buildReportData(
    {
      modelCalls: [
        {
          model_call_timestamp: "2026-07-22T10:00:00Z",
          session_id: "session-1",
          model: "gpt-5.6-sol",
          reasoning_effort: "medium",
          input_tokens: "1000",
          uncached_input_tokens: "300",
          cached_input_tokens: "600",
          cache_write_input_tokens: "100",
          output_tokens: "250",
          reasoning_output_tokens: "50",
          visible_output_tokens: "200",
          total_tokens: "1250",
        },
      ],
      skills: [{ skill_name: "implement" }, { skill_name: "implement" }],
      tools: [
        { tool_name: "Bash", status: "completed", duration_ms: "100" },
        { tool_name: "Bash", status: "started", duration_ms: "" },
        { tool_name: "apply_patch", status: "completed", duration_ms: "50" },
      ],
    },
    pricing,
  );

  assert.deepEqual(report.timeline, [
    {
      date: "2026-07-22",
      uncachedInput: 300,
      cachedInput: 600,
      cacheWrite: 100,
      visibleOutput: 200,
      reasoningOutput: 50,
      estimatedCost: 0.009925,
    },
  ]);
  assert.deepEqual(report.modelReasoning, [
    {
      label: "gpt-5.6-sol / medium",
      tokens: 1250,
      estimatedCost: 0.009925,
    },
  ]);
  assert.deepEqual(report.skills, [{ name: "implement", count: 2 }]);
  assert.deepEqual(report.tools, [
    { name: "Bash", completed: 1, incomplete: 1, averageDurationMs: 100 },
    { name: "apply_patch", completed: 1, incomplete: 0, averageDurationMs: 50 },
  ]);
  assert.equal(report.summary.cacheHitRate, 0.6);
  assert.equal(report.summary.toolCalls, 3);
});
