import { build } from "esbuild";
import path from "node:path";

const reportRoot = path.resolve(import.meta.dirname, "..");

export async function bundleBrowserReport() {
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
