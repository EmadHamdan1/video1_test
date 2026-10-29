import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const renderer = path.join(here, "render-svg.mjs");
const folder = fs.mkdtempSync(path.join(os.tmpdir(), "video1-icon-test-"));
const input = path.join(folder, "test.svg");
const output = path.join(folder, "test.png");
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" fill="currentColor"/></svg>';

try {
  fs.writeFileSync(input, svg, "utf8");
  const result = spawnSync(process.execPath, [renderer, input, output, "128", "#15A89C"], {
    encoding: "utf8",
    timeout: 30000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error("Icon renderer failed: " + (result.stderr || result.stdout || "unknown error"));
  }
  const png = fs.readFileSync(output);
  const pngSignature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (!png.subarray(0, 8).equals(pngSignature)) throw new Error("Renderer output is not a PNG.");
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);
  if (width !== 128 || height !== 128) {
    throw new Error("Unexpected output size: " + width + "x" + height);
  }
  if (png[25] !== 6) throw new Error("Expected RGBA PNG with alpha channel.");
  console.log("SVG renderer smoke test passed: " + width + "x" + height + ", RGBA.");
} finally {
  fs.rmSync(folder, { recursive: true, force: true });
}
