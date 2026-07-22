#!/usr/bin/env node

import path from "node:path";

import { commandOptions, generateReport } from "./generate-report-core.mjs";

const options = commandOptions(process.argv.slice(2), {
  inputDirectory: process.cwd(),
  outputPath: path.resolve("hooks-report.html"),
});
const outputPath = await generateReport({
  ...options,
  browserBundle: __BROWSER_BUNDLE__,
  pricing: __PRICING__,
});
console.log(`Generated ${outputPath}`);
