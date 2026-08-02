#!/usr/bin/env node
/**
 * CLI for the de-marking transform.
 *
 * Two modes, and both arms are meant to go through this tool:
 *
 *   --mode normalize   parse and re-serialize, no rules   -> the explicit arm
 *   --mode demark      parse, apply D1-D4/D7, serialize   -> the implicit arm
 *
 * Running the explicit arm through `normalize` is not cosmetic. Serialization
 * rewrites markdown formatting, so if only the implicit arm were round-tripped,
 * the arms would differ in formatting as well as marking and "nothing else
 * differs" would be false.
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { parseArgs } from "node:util";
import { demark, summarize } from "./demark.js";
import { normalize } from "./mdx.js";
import { loadTemplates, TemplateError } from "./templates.js";
import { RULE_IDS, type RuleId, type RuleSet } from "./types.js";

const USAGE = `
demark — mechanical de-marking transform (D1-D4, D7)

Usage:
  demark --mode <normalize|demark> --in <file.mdx> [options]

Options:
  --mode <m>        normalize (explicit arm) or demark (implicit arm)   [required]
  --in <path>       source MDX file                                     [required]
  --out <path>      output file; writes to stdout when omitted
  --templates <p>   template set                                [default: ./templates.json]
  --report <path>   write the JSON transform report here
  --rules <ids>     comma-separated subset, e.g. D1,D3        [default: all; a deviation]
  --require-frozen  fail unless the template set is marked frozen (use after L2)
  --help
`.trim();

function fail(message: string): never {
  process.stderr.write(`demark: ${message}\n`);
  process.exit(1);
}

function parseRules(value: string | undefined): RuleSet | undefined {
  if (value === undefined) return undefined;
  const ids = value
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s !== "");
  for (const id of ids) {
    if (!(RULE_IDS as readonly string[]).includes(id)) {
      fail(`unknown rule "${id}"; known rules are ${RULE_IDS.join(", ")}`);
    }
  }
  return new Set(ids as RuleId[]);
}

function main(): void {
  const { values } = parseArgs({
    options: {
      mode: { type: "string" },
      in: { type: "string" },
      out: { type: "string" },
      templates: { type: "string", default: "templates.json" },
      report: { type: "string" },
      rules: { type: "string" },
      "require-frozen": { type: "boolean", default: false },
      help: { type: "boolean", default: false },
    },
    allowPositionals: false,
  });

  if (values.help) {
    process.stdout.write(`${USAGE}\n`);
    return;
  }
  if (values.mode !== "normalize" && values.mode !== "demark") {
    fail(`--mode must be "normalize" or "demark"\n\n${USAGE}`);
  }
  if (values.in === undefined) fail(`--in is required\n\n${USAGE}`);

  const inPath = resolve(values.in);
  const source = readFileSync(inPath, "utf8");

  let output: string;
  let reportJson: string | undefined;

  if (values.mode === "normalize") {
    output = normalize(source);
  } else {
    let templates;
    try {
      templates = loadTemplates(resolve(values.templates));
    } catch (error) {
      if (error instanceof TemplateError) fail(error.message);
      throw error;
    }

    if (values["require-frozen"] && !templates.frozen) {
      fail(
        `template set ${templates.version} is not frozen, and --require-frozen was given. ` +
          `Set "frozen": true in the instrument-lock (L2) commit.`,
      );
    }

    const rules = parseRules(values.rules);
    const result = demark(source, {
      templates,
      file: values.in,
      ...(rules ? { rules } : {}),
    });

    output = result.mdx;
    reportJson = `${JSON.stringify(result.report, null, 2)}\n`;

    const counts = summarize(result.report);
    const summary = Object.entries(counts)
      .map(([rule, n]) => `${rule}=${n}`)
      .join(" ");
    process.stderr.write(
      `demark: ${values.in} — ${summary || "no rules fired"}` +
        `${result.report.exceptions.length > 0 ? `, ${result.report.exceptions.length} exception(s)` : ""}\n`,
    );
    for (const exception of result.report.exceptions) {
      process.stderr.write(
        `  exception ${exception.rule}${exception.line ? ` (line ${exception.line})` : ""}: ${exception.reason}\n`,
      );
    }
  }

  if (values.out === undefined) {
    process.stdout.write(output);
  } else {
    const outPath = resolve(values.out);
    mkdirSync(dirname(outPath), { recursive: true });
    writeFileSync(outPath, output, "utf8");
  }

  if (values.report !== undefined && reportJson !== undefined) {
    const reportPath = resolve(values.report);
    mkdirSync(dirname(reportPath), { recursive: true });
    writeFileSync(reportPath, reportJson, "utf8");
  }
}

main();
