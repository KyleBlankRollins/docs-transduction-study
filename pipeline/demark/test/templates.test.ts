import { describe, expect, it } from "vitest";
import { fill, ordinal, parseTemplates, TemplateError } from "../src/templates.js";
import { templates } from "./helpers.js";

const valid = JSON.stringify(templates);

describe("template validation", () => {
  it("accepts the committed template set", () => {
    expect(() => parseTemplates(valid)).not.toThrow();
  });

  it("starts unfrozen, so L2 has something to change", () => {
    expect(templates.frozen).toBe(false);
  });

  it("rejects lowercase D4 keys, which would silently never match", () => {
    const broken = { ...templates, d4_force_keywords: { must: "must" } };
    expect(() => parseTemplates(JSON.stringify(broken))).toThrow(TemplateError);
  });

  it("rejects a D2 option prefix missing its {label} placeholder", () => {
    const broken = {
      ...templates,
      d2_membership: { ...templates.d2_membership, option_prefix: "If you are using this:" },
    };
    expect(() => parseTemplates(JSON.stringify(broken))).toThrow(/\{label\}/);
  });

  it("rejects an empty force phrase, which would drop force silently", () => {
    const broken = { ...templates, d3_force_aside: { ...templates.d3_force_aside, caution: "" } };
    expect(() => parseTemplates(JSON.stringify(broken))).toThrow(TemplateError);
  });
});

describe("fill", () => {
  it("substitutes known placeholders and leaves unknown ones intact", () => {
    expect(fill("If you are using {label}:", { label: "npm" })).toBe("If you are using npm:");
    expect(fill("{a} and {b}", { a: "x" })).toBe("x and {b}");
  });
});

describe("ordinal", () => {
  const t = templates.d1_sequence;

  it("marks the last step so a reader knows where the sequence ends", () => {
    expect(ordinal(t, 2, 3)).toBe(t.final);
  });

  it("uses positional ordinals before the last step", () => {
    expect(ordinal(t, 0, 3)).toBe("First,");
    expect(ordinal(t, 1, 3)).toBe("Second,");
  });

  it("falls back to the overflow connective past the ordinal list", () => {
    expect(ordinal(t, 50, 99)).toBe(t.overflow);
  });

  it("does not call a lone step 'Finally'", () => {
    expect(ordinal(t, 0, 1)).toBe("First,");
  });
});
