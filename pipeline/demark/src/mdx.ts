/**
 * The MDX processor.
 *
 * The same plugin set parses and serializes both arms. That matters more than it
 * looks: serializing normalizes markdown formatting (bullet characters, escapes,
 * fence styles), so if only the implicit arm were round-tripped, formatting noise
 * would differ between arms and the design's "nothing else differs" claim would
 * be false. Run both arms through this processor — the explicit arm with no rules
 * applied — so normalization is held constant and the diff isolates the
 * manipulation.
 */

import remarkDirective from "remark-directive";
import remarkFrontmatter from "remark-frontmatter";
import remarkGfm from "remark-gfm";
import remarkMdx from "remark-mdx";
import remarkParse from "remark-parse";
import remarkStringify, { type Options as StringifyOptions } from "remark-stringify";
import { unified, type Processor } from "unified";
import type { Root } from "mdast";

/**
 * Fixed serialization settings. Committed rather than defaulted so that a
 * remark-stringify default change between versions cannot silently reformat the
 * corpus underneath a locked instrument.
 */
export const STRINGIFY_OPTIONS: StringifyOptions = {
  bullet: "-",
  emphasis: "_",
  strong: "*",
  fence: "`",
  fences: true,
  rule: "-",
  listItemIndent: "one",
  resourceLink: false,
  tightDefinitions: true,
};

export function createProcessor(): Processor<Root, undefined, undefined, Root, string> {
  return unified()
    .use(remarkParse)
    .use(remarkFrontmatter, ["yaml"])
    .use(remarkGfm)
    .use(remarkMdx)
    .use(remarkDirective)
    .use(remarkStringify, STRINGIFY_OPTIONS) as unknown as Processor<
    Root,
    undefined,
    undefined,
    Root,
    string
  >;
}

export function parseMdx(source: string): Root {
  return createProcessor().parse(source);
}

export function stringifyMdx(tree: Root): string {
  return createProcessor().stringify(tree);
}

/**
 * Parse and re-serialize without transforming.
 *
 * This is how the explicit arm is prepared: byte-for-byte differences from
 * Astro's source are formatting only, and holding them constant across arms
 * removes them as a confound.
 */
export function normalize(source: string): string {
  return stringifyMdx(parseMdx(source));
}
