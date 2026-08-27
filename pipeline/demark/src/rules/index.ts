import type { RuleId } from "../types.js";
import { d1Steps } from "./d1-steps.js";
import { d2Tabs } from "./d2-tabs.js";
import { d3Asides } from "./d3-asides.js";
import { d4Keywords } from "./d4-keywords.js";
import { d7Tables } from "./d7-tables.js";
import { d8Prerequisite } from "./d8-prerequisite.js";
import type { Rule } from "./rule.js";

/**
 * Application order.
 *
 * Container rules run in the fixpoint loop. Order within a pass determines
 * which containers get de-marked first; since all run each pass and nesting
 * is resolved by the fixpoint, order is primarily for determinism.
 */
export const RULES: readonly Rule[] = [
  d1Steps,
  d2Tabs,
  d3Asides,
  d7Tables,
  d8Prerequisite,
  d4Keywords,
];

export const RULES_BY_ID: ReadonlyMap<RuleId, Rule> = new Map(RULES.map((r) => [r.id, r]));

export { d1Steps, d2Tabs, d3Asides, d4Keywords, d7Tables, d8Prerequisite };
export type { Rule, RuleContext } from "./rule.js";
