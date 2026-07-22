import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { promisify } from "node:util";

import { buildStandaloneReportGenerator } from "../scripts/build-standalone.mjs";

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
      path.join(tempDirectory, "hooks_events.csv"),
      [
        "event_timestamp,session_id,prompt,last_assistant_message",
        '2026-07-22T09:58:00Z,session-1,"Please improve the report labels.",',
        '2026-07-22T10:05:00Z,session-1,,"Improved report session labels."',
      ].join("\n"),
    );
    await writeFile(
      path.join(tempDirectory, "hooks_skill_invocations.csv"),
      "session_id,skill_name\nsession-1,implement\nsession-1,implement\n",
    );
    await writeFile(
      path.join(tempDirectory, "hooks_tool_calls.csv"),
      "session_id,tool_name,status,duration_ms\nsession-1,Bash,completed,100\n",
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
    assert.match(html, /<select id="session-filter">/);
    assert.match(html, /All sessions/);
    assert.match(html, /reportsBySession/);
    assert.match(html, /2026-07-22T09:58:00Z/);
    assert.match(html, /Improved report session labels\./);
    assert.match(html, /gpt-5\.6-sol/);
    assert.match(html, /Share of all calls/);
    assert.doesNotMatch(html, /<script[^>]+src=/);
  } finally {
    await rm(tempDirectory, { recursive: true, force: true });
  }
});

test("standalone generator needs no repository or installed packages at runtime", async () => {
  const tempDirectory = await mkdtemp(
    path.join(os.tmpdir(), "codex-hooks-standalone-"),
  );
  const generatorPath = path.join(tempDirectory, "generate-hooks-report.mjs");
  const workspacePath = path.join(tempDirectory, "workspace");
  try {
    await mkdir(workspacePath);
    await writeFile(
      path.join(workspacePath, "hooks_model_calls.csv"),
      [
        "model_call_timestamp,session_id,model,reasoning_effort,input_tokens,cached_input_tokens,cache_write_input_tokens,uncached_input_tokens,output_tokens,reasoning_output_tokens,visible_output_tokens,total_tokens",
        "2026-07-22T10:00:00Z,session-1,gpt-5.6-sol,medium,1000,600,100,300,250,50,200,1250",
      ].join("\n"),
    );
    await writeFile(
      path.join(workspacePath, "hooks_skill_invocations.csv"),
      "session_id,skill_name\nsession-1,implement\n",
    );
    await writeFile(
      path.join(workspacePath, "hooks_tool_calls.csv"),
      "session_id,tool_name,status,duration_ms\nsession-1,Bash,completed,100\n",
    );

    await buildStandaloneReportGenerator(generatorPath);
    await execFileAsync(process.execPath, [generatorPath], {
      cwd: workspacePath,
    });

    const html = await readFile(
      path.join(workspacePath, "hooks-report.html"),
      "utf8",
    );
    assert.match(html, /Token usage over time/);
    assert.match(html, /gpt-5\.6-sol/);
    assert.doesNotMatch(html, /<script[^>]+src=/);
  } finally {
    await rm(tempDirectory, { recursive: true, force: true });
  }
});

test("checked-in standalone generator matches the report sources", async () => {
  const tempDirectory = await mkdtemp(
    path.join(os.tmpdir(), "codex-hooks-build-"),
  );
  const generatedPath = path.join(tempDirectory, "generate_hooks_report.mjs");
  try {
    await buildStandaloneReportGenerator(generatedPath);
    assert.equal(
      await readFile(generatedPath, "utf8"),
      await readFile(
        path.join(reportRoot, "bin", "generate_hooks_report.mjs"),
        "utf8",
      ),
    );
  } finally {
    await rm(tempDirectory, { recursive: true, force: true });
  }
});
