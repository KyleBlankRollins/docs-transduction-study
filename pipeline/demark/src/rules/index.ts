import type { RuleId } from "../types.js";
import { d1Steps } from "./d1-steps.js";
import { d2Tabs } from "./d2-tabs.js";
import { d3Asides } from "./d3-asides.js";
import { d4Keywords } from "./d4-keywords.js";
import { d7Tables } from "./d7-tables.js";
import type { Rule } from "./rule.js";

/**
 * Application order.
 *
 * Container rules (D1, D2, D3) run before D4 so that keywords lifted out of a
 * Steps block, a tab panel, or an aside are still de-marked. D7 is independent.
 */
export const RULES: readonly Rule[] = [d1Steps, d2Tabs, d3Asides, d7Tables, d4Keywords];

export const RULES_BY_ID: ReadonlyMap<RuleId, Rule> = new Map(RULES.map((r) => [r.id, r]));

export { d1Steps, d2Tabs, d3Asides, d4Keywords, d7Tables };
export type { Rule, RuleContext } from "./rule.js";
