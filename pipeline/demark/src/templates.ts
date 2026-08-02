/**
 * Loading and validation for the frozen template set.
 *
 * The templates are the manipulation, so they are validated rather than trusted:
 * a typo that silently drops a force phrase would bias the implicit arm in the
 * direction the hypothesis predicts, which is the one failure mode this project
 * can least afford to discover after coding.
 */

import { readFileSync } from "node:fs";
import { z } from "zod";

/**
 * Recursively drops `$comment` keys.
 *
 * templates.json is annotated heavily on purpose — it is the manipulation, and
 * the reasoning behind each phrase belongs next to the phrase. Stripping happens
 * before validation so annotations cannot be mistaken for data: a `$comment`
 * left inside `d4_force_keywords` would otherwise register as a keyword.
 */
function stripComments(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stripComments);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => key !== "$comment")
        .map(([key, child]) => [key, stripComments(child)]),
    );
  }
  return value;
}

const nonEmpty = z.string().min(1);

const TemplatesSchema = z.object({
  version: nonEmpty,
  frozen: z.boolean(),

  d1_sequence: z.object({
    ordinals: z.array(nonEmpty).min(1),
    overflow: nonEmpty,
    final: nonEmpty,
    lead_in: nonEmpty,
  }),

  d2_membership: z.object({
    lead_in: nonEmpty,
    option_prefix: nonEmpty.refine((s) => s.includes("{label}"), {
      message: "d2_membership.option_prefix must contain {label}",
    }),
  }),

  d3_force_aside: z.object({
    note: nonEmpty,
    tip: nonEmpty,
    caution: nonEmpty,
    danger: nonEmpty,
    default: nonEmpty,
    titled: nonEmpty.refine((s) => s.includes("{title}"), {
      message: "d3_force_aside.titled must contain {title}",
    }),
  }),

  /**
   * Keys are matched as whole words in ALL CAPS only (RFC 8174). Enforced here
   * so a lowercase key cannot silently disable a substitution.
   */
  d4_force_keywords: z
    .record(nonEmpty, nonEmpty)
    .refine(
      (map) => Object.keys(map).every((k) => k === k.toUpperCase()),
      { message: "d4_force_keywords keys must be ALL CAPS (RFC 8174)" },
    ),

  d7_precondition_table: z.object({
    lead_in: nonEmpty,
    row_prefix: nonEmpty.refine((s) => s.includes("{first_cell}"), {
      message: "d7_precondition_table.row_prefix must contain {first_cell}",
    }),
    cell_pattern: nonEmpty
      .refine((s) => s.includes("{header}") && s.includes("{value}"), {
        message: "d7_precondition_table.cell_pattern must contain {header} and {value}",
      }),
    cell_separator: z.string(),
    row_terminator: z.string(),
  }),
});

export type Templates = z.infer<typeof TemplatesSchema>;

export class TemplateError extends Error {
  override name = "TemplateError";
}

/** Parses and validates a template set from a JSON string. */
export function parseTemplates(json: string, source = "<inline>"): Templates {
  let raw: unknown;
  try {
    raw = JSON.parse(json);
  } catch (cause) {
    throw new TemplateError(`${source}: not valid JSON: ${(cause as Error).message}`);
  }

  const result = TemplatesSchema.safeParse(stripComments(raw));
  if (!result.success) {
    const issues = result.error.issues
      .map((i) => `  ${i.path.join(".") || "(root)"}: ${i.message}`)
      .join("\n");
    throw new TemplateError(`${source}: template set is invalid:\n${issues}`);
  }
  return result.data;
}

export function loadTemplates(path: string): Templates {
  return parseTemplates(readFileSync(path, "utf8"), path);
}

/** Replaces `{placeholder}` occurrences. Unknown placeholders are left intact. */
export function fill(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    Object.hasOwn(values, key) ? (values[key] as string) : match,
  );
}

/**
 * Ordinal connective for position `index` in a sequence of `total` items.
 *
 * The last item uses the `final` template so the sequence has an audible end —
 * a reader who cannot see step boundaries still needs to know where they stop.
 */
export function ordinal(t: Templates["d1_sequence"], index: number, total: number): string {
  if (total > 1 && index === total - 1) return t.final;
  return t.ordinals[index] ?? t.overflow;
}
