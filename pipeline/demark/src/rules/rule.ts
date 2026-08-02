import type { Root } from "mdast";
import type { Templates } from "../templates.js";
import type { RuleException, RuleHit, RuleId } from "../types.js";

export interface RuleContext {
  templates: Templates;
  hits: RuleHit[];
  exceptions: RuleException[];
}

export interface Rule {
  readonly id: RuleId;
  readonly description: string;
  apply(tree: Root, ctx: RuleContext): void;
}

export function record(ctx: RuleContext, rule: RuleId, detail: string, line: number | undefined): void {
  ctx.hits.push({ rule, detail, line });
}

export function except(ctx: RuleContext, rule: RuleId, reason: string, line: number | undefined): void {
  ctx.exceptions.push({ rule, reason, line });
}
