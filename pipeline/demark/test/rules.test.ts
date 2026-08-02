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
    expect(out(":::note\nRestart the server.\n:::\n")).toContain("Note that restart");
  });

  it("does not lowercase a proper noun or acronym", () => {
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
