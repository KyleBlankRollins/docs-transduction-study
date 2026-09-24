import remarkMdx from "remark-mdx";
import remarkParse from "remark-parse";
import { unified } from "unified";
import { describe, expect, it } from "vitest";
import { buildKeywordPattern } from "../src/rules/d4-keywords.js";
import { out, run, templates } from "./helpers.js";

describe("D1 — Steps to prose", () => {
  const source = `
<Steps>

1. Install the package.

   \`\`\`sh
   npm install astro
   \`\`\`

2. Start the dev server.

3. Open the browser.

</Steps>
`;

  it("removes the component and states the order in words", () => {
    const result = out(source);
    expect(result).not.toContain("<Steps>");
    expect(result).toContain(templates.d1_sequence.lead_in);
    expect(result).toContain("First,");
    expect(result).toContain("Second,");
    expect(result).toContain("Finally,");
  });

  it("preserves the code block rather than flattening it into prose", () => {
    expect(out(source)).toContain("npm install astro");
  });

  it("keeps steps in source order", () => {
    const result = out(source);
    expect(result.indexOf("First,")).toBeLessThan(result.indexOf("Second,"));
    expect(result.indexOf("Second,")).toBeLessThan(result.indexOf("Finally,"));
  });

  it("reports one hit carrying the step count", () => {
    const { report } = run(source);
    const hits = report.hits.filter((h) => h.rule === "D1");
    expect(hits).toHaveLength(1);
    expect(hits[0]?.detail).toContain("3 steps");
  });
});

describe("D2 — Tabs to prose enumeration", () => {
  const source = `
<Tabs>
  <TabItem label="npm">

    \`\`\`sh
    npm install
    \`\`\`

  </TabItem>
  <TabItem label="pnpm">

    \`\`\`sh
    pnpm install
    \`\`\`

  </TabItem>
</Tabs>
`;

  it("states the alternatives relation in words, which the tabs carried structurally", () => {
    const result = out(source);
    expect(result).not.toContain("<Tabs>");
    expect(result).toContain(templates.d2_membership.lead_in);
    expect(result).toMatch(/alternatives/i);
  });

  it("keeps every option and its label", () => {
    const result = out(source);
    expect(result).toContain("npm");
    expect(result).toContain("pnpm");
    expect(result).toContain("npm install");
    expect(result).toContain("pnpm install");
  });

  it("raises an exception rather than guessing when a label is not literal", () => {
    const { report } = run(`
<Tabs>
  <TabItem label={pkg}>

    Text.

  </TabItem>
</Tabs>
`);
    expect(report.hits.filter((h) => h.rule === "D2")).toHaveLength(0);
    expect(report.exceptions.some((e) => e.rule === "D2")).toBe(true);
  });

  it("recognises custom tab wrapper PackageManagerTabs", () => {
    const result = out("\n<PackageManagerTabs>\n  <Fragment slot=\"npm\">\n\n    npm content\n\n  </Fragment>\n  <Fragment slot=\"pnpm\">\n\n    pnpm content\n\n  </Fragment>\n</PackageManagerTabs>\n");
    expect(result).not.toContain("PackageManagerTabs");
    expect(result).toContain("If you are using npm");
    expect(result).toContain("If you are using pnpm");
  });

  it("recognises UIFrameworkTabs with slot-based fragments", () => {
    const result = out("\n<UIFrameworkTabs>\n  <Fragment slot=\"react\">\n\n    React content\n\n  </Fragment>\n  <Fragment slot=\"vue\">\n\n    Vue content\n\n  </Fragment>\n</UIFrameworkTabs>\n");
    expect(result).not.toContain("UIFrameworkTabs");
    expect(result).toContain("If you are using react");
    expect(result).toContain("If you are using vue");
  });
});

describe("D3 — Asides to inline prose", () => {
  it("carries the force of a caution into ordinary words", () => {
    const result = out(`
:::caution
Deleting the config removes your site settings.
:::
`);
    expect(result).not.toContain(":::");
    expect(result).toContain(templates.d3_force_aside.caution);
    expect(result).toContain("your site settings");
  });

  it("distinguishes danger from caution rather than pooling them", () => {
    const danger = out(":::danger\nThis erases the database.\n:::\n");
    expect(danger).toContain(templates.d3_force_aside.danger);
    expect(danger).not.toContain(templates.d3_force_aside.caution);
  });

  it("uses a custom aside title when one is given", () => {
    const result = out(":::note[Before you start]\nInstall Node first.\n:::\n");
    expect(result).toContain("Before you start:");
  });

  it("handles the component spelling of an aside too", () => {
    const result = out(`
<Aside type="tip">
Use the dev server for faster feedback.
</Aside>
`);
    expect(result).not.toContain("<Aside");
    expect(result).toContain(templates.d3_force_aside.tip);
  });

  it("lowercases the following sentence so the prose does not read as machine-made", () => {
    expect(out(":::note\nRestart the server.\n:::\n")).toContain("Note: Restart");
  });

  it("does not lowercase a proper noun or acronym — decapitalization is removed", () => {
    expect(out(":::note\nTypeScript is required here.\n:::\n")).toContain("TypeScript");
    expect(out(":::note\nURL rewriting applies.\n:::\n")).toContain("URL");
  });
});

describe("D4 — normative keywords to ordinary modals", () => {
  it("matches ALL CAPS only, per RFC 8174", () => {
    const result = out("You MUST restart. You must already know this.\n");
    expect(result).not.toContain("MUST");
    expect(result).toContain("must restart");
  });

  it("never turns a prohibition into an obligation", () => {
    expect(out("You MUST NOT commit secrets.\n")).toContain("must not commit");
  });

  it("prefers the longest keyword match", () => {
    const pattern = buildKeywordPattern({ MUST: "must", "MUST NOT": "must not" });
    expect("You MUST NOT do that".replace(pattern, (m) => `<${m}>`)).toContain("<MUST NOT>");
  });

  it("leaves keywords inside code untouched", () => {
    const result = out("Set `MUST_RETRY` to true.\n\n```js\nconst MUST = 1;\n```\n");
    expect(result).toContain("MUST_RETRY");
    expect(result).toContain("const MUST = 1;");
  });

  it("records one hit per keyword occurrence", () => {
    const { report } = run("You MUST restart and you SHOULD verify.\n");
    expect(report.hits.filter((h) => h.rule === "D4")).toHaveLength(2);
  });

  it("stays grammatical, so the arms cannot be told apart on fluency", () => {
    expect(out("You MUST restart the server.\n")).toContain("You must restart the server.");
  });
});

describe("D7 — tables to prose enumeration", () => {
  const source = `
| Flag | Default | Required |
| ---- | ------- | -------- |
| \`--port\` | 4321 | no |
| \`--host\` | localhost | yes |
`;

  it("removes the table and enumerates the rows", () => {
    const result = out(source);
    expect(result).not.toContain("| ----");
    expect(result).toContain(templates.d7_precondition_table.lead_in);
    expect(result).toContain("4321");
    expect(result).toContain("localhost");
  });

  it("preserves inline code in cells rather than flattening it", () => {
    expect(out(source)).toContain("`--port`");
  });

  it("names the column each value came from", () => {
    const result = out(source);
    expect(result).toContain("Default is 4321");
    expect(result).toContain("Required is no");
  });

  it("raises an exception for a header-only table", () => {
    const { report } = run("| A | B |\n| - | - |\n");
    expect(report.exceptions.some((e) => e.rule === "D7")).toBe(true);
  });
});
describe("D8 — prerequisite heading unmarking", () => {
  it("replaces ## Prerequisites with the template lead-in", () => {
    const result = out("## Prerequisites\n\nYou need Node 18+.\n");
    expect(result).not.toContain("## Prerequisites");
    expect(result).toContain(templates.d8_prerequisite_heading.lead_in.trim());
    expect(result).toContain("Node 18+");
  });

  it("replaces ### Requirements with the template lead-in", () => {
    const result = out("### Requirements\n\nInstall pnpm first.\n");
    expect(result).not.toContain("### Requirements");
    expect(result).toContain(templates.d8_prerequisite_heading.lead_in.trim());
    expect(result).toContain("Install pnpm");
  });

  it("records one hit when a heading is de-marked", () => {
    const { report } = run("## Prerequisites\n\nContent here.\n");
    expect(report.hits.filter((h) => h.rule === "D8")).toHaveLength(1);
  });

  it("does not touch non-prerequisite headings", () => {
    const result = out("## Getting Started\n\nContent here.\n");
    expect(result).toContain("## Getting Started");
    const { report } = run("## Getting Started\n\nContent here.\n");
    expect(report.hits.filter((h) => h.rule === "D8")).toHaveLength(0);
  });
});

describe("DM-1 — nested containers (closed by fixpoint)", () => {
  it("de-marks a table inside a step (two-deep nesting)", () => {
    const source = [
      "<Steps>",
      "",
      "1. Install.",
      "",
      "   | Flag  | Value  |",
      "   | ----- | ------ |",
      "   | --port | 4321 |",
      "",
      "2. Deploy.",
      "",
      "</Steps>",
    ].join("\n");
    const result = out(source);
    expect(result).not.toContain("<Steps>");
    expect(result).not.toContain("|---");
    expect(result).toContain("First,");
    expect(result).toContain("Finally,");
    expect(result).toContain("--port");
  });

  it("de-marks an aside inside a step", () => {
    const result = out("\n<Steps>\n\n1. Configure.\n\n   :::caution\n   Backup first.\n   :::\n\n2. Deploy.\n\n</Steps>\n");
    expect(result).not.toContain("<Steps>");
    expect(result).not.toContain(":::");
    expect(result).toContain("First,");
    expect(result).toContain("Finally,");
    expect(result).toContain("Backup first.");
  });
});

describe("Parser integrity — <details>/<summary> inside directives", () => {
  const faqSource = [
    ":::note[FAQ]",
    "",
    "<details>",
    "<summary>**Q: How does this work?**</summary>",
    "",
    "It works via transduction.",
    "",
    "</details>",
    "",
    "<details>",
    "<summary>**Q: Is it safe?**</summary>",
    "",
    "Yes.",
    "",
    "</details>",
    "",
    ":::",
    "",
    "Regular content after the aside.",
  ].join("\n");

  it("puts the force phrase in its own paragraph before block HTML so output is valid MDX (A5)", () => {
    const result = out(faqSource);
    expect(result).toMatch(/^FAQ:\n\n<details>/m);
    // Parse the real output with MDX, without the demark preprocessing that
    // masks <details>; this is the parse the Astro build performs.
    expect(() => unified().use(remarkParse).use(remarkMdx).parse(result)).not.toThrow();
  });

  it("preserves <details> tags inside ::: directives (no placeholder leakage)", () => {
    const result = out(faqSource);
    // The explicit arm (untransformed) has <details> — the transform must
    // keep them byte-identical. Preprocess sanitizes only the parser input;
    // patching operates on the real source.
    expect(result).toContain("<details>");
    expect(result).toContain("</details>");
    expect(result).toContain("<summary>");
    expect(result).toContain("</summary>");
  });

  it("does not leak placeholder text like ' details ' or ' summary ' into output", () => {
    const result = out(faqSource);
    // The preprocessSource function replaces tags with padded space markers.
    // These must never appear in the transform output.
    expect(result).not.toMatch(/^\s+details\s+$/m);
    expect(result).not.toMatch(/^\s+\/details\s+$/m);
    expect(result).not.toMatch(/^\s+summary\s+$/m);
    expect(result).not.toMatch(/^\s+\/summary\s+$/m);
  });

  it("reports a D3 hit for the enclosing aside but no extra hits for the HTML", () => {
    const { report } = run(faqSource);
    const d3Hits = report.hits.filter((h) => h.rule === "D3");
    expect(d3Hits).toHaveLength(1);
    expect(d3Hits[0]?.detail).toContain("note");
  });
});
