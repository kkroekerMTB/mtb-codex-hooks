import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "csv-parse/sync";

import { buildReportData } from "./aggregate.mjs";
import { renderHtml } from "./template.mjs";

export async function generateReport({
  inputDirectory,
  outputPath,
  browserBundle,
  pricing,
}) {
  const inputs = {
    events: await readOptionalCsv(
      path.join(inputDirectory, "hooks_events.csv"),
    ),
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
  const html = renderHtml(reportData, browserBundle);

  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, html, "utf8");
  return outputPath;
}

export function commandOptions(arguments_, defaults) {
  const options = { ...defaults };
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

async function readCsv(filePath) {
  const contents = await readFile(filePath, "utf8");
  return parse(contents, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
  });
}

async function readOptionalCsv(filePath) {
  try {
    return await readCsv(filePath);
  } catch (error) {
    if (error.code === "ENOENT") {
      return [];
    }
    throw error;
  }
}
