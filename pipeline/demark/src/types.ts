/**
 * Shared types for the de-marking transform.
 *
 * Rule IDs match the design document (D1-D4, D7). D5 and D6 were cut in design
 * version 0.3 and the IDs are deliberately not reused.
 */

export const RULE_IDS = ["D1", "D2", "D3", "D4", "D7"] as const;

export type RuleId = (typeof RULE_IDS)[number];

/** One relation site the transform acted on. */
export interface RuleHit {
  rule: RuleId;
  /** What was transformed, for the run log and the equivalence review. */
  detail: string;
  /** 1-indexed source line in the explicit variant, when position is known. */
  line: number | undefined;
}

/**
 * A site the rule recognized but declined to transform mechanically.
 *
 * Exceptions are not silent. The design commits to reporting them with the
 * specimen named, and to reporting the mechanical-manipulation claim as FALSE
 * if they turn out to be frequent.
 */
export interface RuleException {
  rule: RuleId;
  reason: string;
  line: number | undefined;
}

export interface DemarkReport {
  /** Path of the explicit-arm source, relative to the corpus root. */
  file: string;
  templateVersion: string;
  templatesFrozen: boolean;
  hits: RuleHit[];
  exceptions: RuleException[];
}

export interface DemarkResult {
  mdx: string;
  report: DemarkReport;
}

/** Which rules to run. Omitting a rule is a run-log-worthy deviation. */
export type RuleSet = ReadonlySet<RuleId>;

export const ALL_RULES: RuleSet = new Set(RULE_IDS);
