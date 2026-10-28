import fs from "node:fs";
import path from "node:path";
import { Resvg } from "@resvg/resvg-js";

function usage() {
  console.error("Usage: node render-svg.mjs <input.svg> <output.png> [size=256] [color=#159A90]");
  process.exit(2);
}

const [inputPath, outputPath, sizeText = "256", color = "#159A90"] = process.argv.slice(2);
if (!inputPath || !outputPath) usage();

const size = Number(sizeText);
if (!Number.isInteger(size) || size < 32 || size > 2048) {
  throw new Error("Icon render size must be an integer from 32 to 2048.");
}
if (!/^#[0-9a-f]{6}$/i.test(color)) {
  throw new Error("Icon color must be a #RRGGBB value.");
}

const source = fs.readFileSync(inputPath, "utf8");
if (source.length > 1024 * 1024) throw new Error("SVG is larger than the 1 MiB safety limit.");
if (!/<svg\b/i.test(source) || /<script\b|javascript:|<foreignObject\b/i.test(source)) {
  throw new Error("Refusing unsafe or invalid SVG input.");
}
if (/<image\b|(?:href|xlink:href)\s*=\s*["'](?:https?:|file:|\/\/)/i.test(source)) {
  throw new Error("External image references are not allowed in icon SVGs.");
}

const tinted = source.replace(/currentColor/gi, color);
const rendered = new Resvg(tinted, {
  fitTo: { mode: "width", value: size },
}).render();
const png = rendered.asPng();
fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
fs.writeFileSync(outputPath, png);
console.log(JSON.stringify({
  ok: true,
  input: path.resolve(inputPath),
  output: path.resolve(outputPath),
  size,
  width: rendered.width,
  height: rendered.height,
  bytes: png.length,
}));
