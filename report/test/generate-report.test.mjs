import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const reportRoot = path.resolve(import.meta.dirname, "..");

test("generates a self-contained HTML report from the exported CSV files", async () => {
  const tempDirectory = await mkdtemp(path.join(os.tmpdir(), "codex-hooks-report-"));
  const outputPath = path.join(tempDirectory, "hooks-report.html");
  try {
    await writeFile(
      path.join(tempDirectory, "hooks_model_calls.csv"),
      [
        "model_call_timestamp,session_id,model,reasoning_effort,input_tokens,cached_input_tokens,cache_write_input_tokens,uncached_input_tokens,output_tokens,reasoning_output_tokens,visible_output_tokens,total_tokens",
        "2026-07-22T10:00:00Z,session-1,gpt-5.6-sol,medium,1000,600,100,300,250,50,200,1250",
      ].join("\n"),
    );
    await writeFile(
      path.join(tempDirectory, "hooks_skill_invocations.csv"),
      "skill_name\nimplement\nimplement\n",
    );
    await writeFile(
      path.join(tempDirectory, "hooks_tool_calls.csv"),
      "tool_name,status,duration_ms\nBash,completed,100\n",
    );

    await execFileAsync(
      process.execPath,
      [
        "src/generate-report.mjs",
        "--input-dir",
        tempDirectory,
        "--output",
        outputPath,
      ],
      { cwd: reportRoot },
    );

    const html = await readFile(outputPath, "utf8");
    assert.match(html, /Token usage over time/);
    assert.match(html, /Usage by model and reasoning level/);
    assert.match(html, /Skills invoked/);
    assert.match(html, /Tool calls/);
    assert.match(html, /API-equivalent cost/);
    assert.match(html, /gpt-5\.6-sol/);
    assert.match(html, /Share of all calls/);
    assert.doesNotMatch(html, /<script[^>]+src=/);
  } finally {
    await rm(tempDirectory, { recursive: true, force: true });
  }
});
