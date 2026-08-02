import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { demark } from "../src/demark.js";
import { parseTemplates, type Templates } from "../src/templates.js";
import type { DemarkResult } from "../src/types.js";

const TEMPLATES_PATH = fileURLToPath(new URL("../templates.json", import.meta.url));

export const templates: Templates = parseTemplates(readFileSync(TEMPLATES_PATH, "utf8"), "templates.json");

export function run(source: string): DemarkResult {
  return demark(source, { templates, file: "test.mdx" });
}

export function out(source: string): string {
  return run(source).mdx;
}
