#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { bundleBrowserReport } from "../scripts/bundle-browser.mjs";
import { commandOptions, generateReport } from "./generate-report-core.mjs";

const reportRoot = path.resolve(import.meta.dirname, "..");
const repositoryRoot = path.resolve(reportRoot, "..");

async function run(arguments_) {
  const [browserBundle, pricingText] = await Promise.all([
    bundleBrowserReport(),
    readFile(path.join(reportRoot, "pricing", "openai-api.json"), "utf8"),
  ]);
  return generateReport({
    ...commandOptions(arguments_, {
      inputDirectory: repositoryRoot,
      outputPath: path.join(reportRoot, "dist", "hooks-report.html"),
    }),
    browserBundle,
    pricing: JSON.parse(pricingText),
  });
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  console.log(`Generated ${await run(process.argv.slice(2))}`);
}
