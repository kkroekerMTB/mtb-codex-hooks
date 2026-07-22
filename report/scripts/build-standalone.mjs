#!/usr/bin/env node

import { build } from "esbuild";
import { chmod, mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { bundleBrowserReport } from "./bundle-browser.mjs";

const reportRoot = path.resolve(import.meta.dirname, "..");
const defaultOutputPath = path.join(
  reportRoot,
  "bin",
  "generate_hooks_report.mjs",
);

export async function buildStandaloneReportGenerator(
  outputPath = defaultOutputPath,
) {
  const [browserBundle, pricingText] = await Promise.all([
    bundleBrowserReport(),
    readFile(path.join(reportRoot, "pricing", "openai-api.json"), "utf8"),
  ]);
  await mkdir(path.dirname(outputPath), { recursive: true });
  await build({
    entryPoints: [path.join(reportRoot, "src", "standalone-entry.mjs")],
    bundle: true,
    define: {
      __BROWSER_BUNDLE__: JSON.stringify(browserBundle),
      __PRICING__: JSON.stringify(JSON.parse(pricingText)),
    },
    format: "esm",
    minify: true,
    outfile: outputPath,
    platform: "node",
    target: ["node20"],
  });
  await chmod(outputPath, 0o755);
  return outputPath;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  const outputIndex = process.argv.indexOf("--output");
  if (outputIndex >= 0 && !process.argv[outputIndex + 1]) {
    throw new Error("--output requires a path");
  }
  if (outputIndex > 2 || (outputIndex < 0 && process.argv.length > 2)) {
    throw new Error("Usage: build-standalone.mjs [--output <path>]");
  }
  const outputPath = outputIndex < 0
    ? defaultOutputPath
    : path.resolve(process.argv[outputIndex + 1]);
  console.log(`Built ${await buildStandaloneReportGenerator(outputPath)}`);
}
