#!/usr/bin/env node

import { build } from "esbuild";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "csv-parse/sync";

import { buildReportData } from "./aggregate.mjs";
import { renderHtml } from "./template.mjs";

const reportRoot = path.resolve(import.meta.dirname, "..");
const repositoryRoot = path.resolve(reportRoot, "..");

export async function generateReport({ inputDirectory, outputPath }) {
  const pricing = JSON.parse(
    await readFile(path.join(reportRoot, "pricing", "openai-api.json"), "utf8"),
  );
  const inputs = {
    modelCalls: await readCsv(path.join(inputDirectory, "hooks_model_calls.csv")),
    skills: await readCsv(
      path.join(inputDirectory, "hooks_skill_invocations.csv"),
    ),
    tools: await readCsv(path.join(inputDirectory, "hooks_tool_calls.csv")),
  };
  const reportData = {
    ...buildReportData(inputs, pricing),
    generatedAt: new Date().toISOString(),
  };
  const browserBundle = await bundleBrowserReport();
  const html = renderHtml(reportData, browserBundle);

  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, html, "utf8");
  return outputPath;
}

async function readCsv(filePath) {
  const contents = await readFile(filePath, "utf8");
  return parse(contents, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
  });
}

async function bundleBrowserReport() {
  const result = await build({
    entryPoints: [path.join(reportRoot, "src", "report-browser.mjs")],
    bundle: true,
    format: "iife",
    minify: true,
    platform: "browser",
    target: ["es2020"],
    write: false,
  });
  return result.outputFiles[0].text;
}

function commandOptions(arguments_) {
  const options = {
    inputDirectory: repositoryRoot,
    outputPath: path.join(reportRoot, "dist", "hooks-report.html"),
  };
  for (let index = 0; index < arguments_.length; index += 1) {
    const argument = arguments_[index];
    const value = arguments_[index + 1];
    if (argument === "--input-dir" && value) {
      options.inputDirectory = path.resolve(value);
      index += 1;
    } else if (argument === "--output" && value) {
      options.outputPath = path.resolve(value);
      index += 1;
    } else {
      throw new Error(`Unknown or incomplete argument: ${argument}`);
    }
  }
  return options;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const outputPath = await generateReport(commandOptions(process.argv.slice(2)));
  console.log(`Generated ${outputPath}`);
}
