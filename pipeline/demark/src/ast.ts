/**
 * Small AST helpers shared by the de-marking rules.
 *
 * Nothing here makes an editorial decision. Anything that chooses words lives in
 * templates.json.
 */

import type { BlockContent, DefinitionContent, Node, Paragraph, PhrasingContent, Root, RootContent } from "mdast";
import type { MdxJsxFlowElement } from "mdast-util-mdx";
import type { ContainerDirective } from "mdast-util-directive";

export type BlockNode = BlockContent | DefinitionContent;

export function lineOf(node: Node): number | undefined {
  return node.position?.start.line;
}

export function isMdxJsxFlowElement(node: Node): node is MdxJsxFlowElement {
  return node.type === "mdxJsxFlowElement";
}

/** True when `node` is an MDX JSX block element with the given tag name. */
export function isJsxElement(node: Node, name: string): node is MdxJsxFlowElement {
  return isMdxJsxFlowElement(node) && node.name === name;
}

export function isContainerDirective(node: Node): node is ContainerDirective {
  return node.type === "containerDirective";
}

/** Reads a literal string JSX attribute. Expression attributes return undefined. */
export function jsxAttr(node: MdxJsxFlowElement, name: string): string | undefined {
  for (const attr of node.attributes) {
    if (attr.type !== "mdxJsxAttribute" || attr.name !== name) continue;
    if (typeof attr.value === "string") return attr.value;
    return undefined;
  }
  return undefined;
}

/** Recursively collects visible text. Used for labels and table cells, not content. */
export function textOf(node: Node): string {
  if ("value" in node && typeof node.value === "string") return node.value;
  if ("children" in node && Array.isArray(node.children)) {
    return (node.children as Node[]).map(textOf).join("");
  }
  return "";
}

export function paragraph(children: PhrasingContent[]): Paragraph {
  return { type: "paragraph", children };
}

export function textParagraph(value: string): Paragraph {
  return paragraph([{ type: "text", value }]);
}

/**
 * Prefixes a phrase onto an existing paragraph, lowercasing the following word
 * when it looks like an ordinary capitalized sentence start.
 *
 * Without this, D3 produces "Note that Restart the server" — visibly machine-made
 * in a way that would let a reader distinguish the arms on fluency rather than on
 * marking, which is a confound and not a subtle one.
 */
export function prefixParagraph(target: Paragraph, phrase: string): Paragraph {
  const [first, ...rest] = target.children;
  if (first?.type === "text") {
    return paragraph([
      { type: "text", value: `${phrase} ${decapitalize(first.value)}` },
      ...rest,
    ]);
  }
  return paragraph([{ type: "text", value: `${phrase} ` }, ...target.children]);
}

/**
 * Lowercases a leading word unless it looks like a proper noun, an acronym, or
 * an identifier — "TypeScript", "URL", and "MDX" must survive intact.
 */
export function decapitalize(value: string): string {
  const match = /^(\s*)([A-Z])([a-z]+)(\b)/.exec(value);
  if (!match) return value;
  const [, space = "", head = "", tail = ""] = match;
  return `${space}${head.toLowerCase()}${tail}${value.slice(match[0].length)}`;
}

/** Ensures a block sequence ends with sentence punctuation on its last paragraph. */
export function ensureTerminated(nodes: BlockNode[], terminator = "."): BlockNode[] {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const node = nodes[i];
    if (node?.type !== "paragraph") continue;
    const last = node.children.at(-1);
    if (last?.type === "text" && !/[.!?:;]\s*$/.test(last.value)) {
      last.value = `${last.value.trimEnd()}${terminator}`;
    }
    break;
  }
  return nodes;
}

/** Replaces `parent.children[index]` with zero or more nodes. */
export function replaceAt(
  parent: Root | { children: RootContent[] },
  index: number,
  replacement: BlockNode[],
): void {
  (parent.children as unknown as BlockNode[]).splice(index, 1, ...replacement);
}
