#!/usr/bin/env node
// setup-vitepress.mjs
//
// Reads <wiki-dir>/.wiki-meta.json and emits a complete VitePress configuration
// inside <wiki-dir>/. The wiki directory becomes a self-contained VitePress project:
//
//   <wiki-dir>/
//   ├── .vitepress/
//   │   ├── config.ts          (regenerated every run — skill-owned)
//   │   └── theme/
//   │       └── index.ts       (written only if missing — user-owned after first write)
//   ├── package.json           (regenerated every run — skill-owned)
//   └── ...existing markdown pages
//
// The adapter is idempotent: re-running it after the wiki is regenerated
// rewrites config.ts and package.json from the current manifest.
// User-created files under .vitepress/theme/ (other than index.ts) are preserved.
//
// Usage:
//   node setup-vitepress.mjs <wiki-dir> [--title "Custom title"] [--description "..."]

import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_NAME = basename(process.argv[1] ?? 'setup-vitepress.mjs');

// ---------------------------------------------------------------------------
// CLI parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { wikiDir: null, title: null, description: null, help: false };
  const positional = [];
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-h' || a === '--help') args.help = true;
    else if (a === '--title') args.title = argv[++i] ?? '';
    else if (a === '--description') args.description = argv[++i] ?? '';
    else if (a.startsWith('--title=')) args.title = a.slice('--title='.length);
    else if (a.startsWith('--description=')) args.description = a.slice('--description='.length);
    else positional.push(a);
  }
  if (positional.length > 0) args.wikiDir = positional[0];
  return args;
}

function printHelp() {
  console.log(`Usage: node ${SCRIPT_NAME} <wiki-dir> [options]

Reads <wiki-dir>/.wiki-meta.json and emits a VitePress configuration.

Options:
  --title <text>         Override the site title (default: first page's H1)
  --description <text>   Override the site description
  -h, --help             Show this help

What it writes (all inside <wiki-dir>):
  .vitepress/config.ts        Sidebar, nav, search, Mermaid (always overwritten)
  .vitepress/theme/index.ts   Theme entry point (only if missing)
  .vitepress/theme/custom.css Brand color overrides (only if missing)
  package.json                VitePress deps and scripts (always overwritten)

After running, the user runs:
  npm install
  npm run docs:dev   # or: npm run docs:build
`);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function humanize(name) {
  // Sentence-case label from a kebab-case section name, matching the wiki's
  // own sentence-case heading convention (see "Human writing rules" in SKILL.md).
  //   "by-the-numbers"      -> "By the numbers"
  //   "how-to-contribute"   -> "How to contribute"
  //   "cleanup-opportunities" -> "Cleanup opportunities"
  //   "api"                 -> "API"   (acronyms stay upper)
  //   "tui-rendering"       -> "TUI rendering"
  const acronyms = new Set(['api', 'cli', 'tui', 'sdk', 'css', 'html', 'http', 'https', 'sql', 'ui', 'url', 'json', 'yaml', 'tcp', 'udp', 'tls', 'dns', 'cdn']);
  const words = name.split('-');
  return words
    .map((w, i) => {
      if (acronyms.has(w)) return w.toUpperCase();
      if (i === 0) return w.charAt(0).toUpperCase() + w.slice(1);
      return w;
    })
    .join(' ');
}

function readTitle(filePath) {
  // Read the first "# Heading" line from a markdown file.
  // Falls back to the filename stem if no H1 is found.
  let content;
  try {
    content = readFileSync(filePath, 'utf8');
  } catch {
    return basename(filePath, '.md');
  }
  for (const line of content.split('\n')) {
    const m = line.match(/^#\s+(.+?)\s*$/);
    if (m) return m[1].trim();
  }
  return basename(filePath, '.md');
}

function toLink(mdPath) {
  // Convert a wiki-relative markdown path to a VitePress link.
  //   overview/index.md        -> /overview/
  //   overview/architecture.md -> /overview/architecture
  //   apps/cli/index.md        -> /apps/cli/
  //   apps/cli/tui-rendering.md -> /apps/cli/tui-rendering
  //   lore.md                  -> /lore
  //   index.md                 -> /
  const noExt = mdPath.replace(/\.md$/, '');
  if (noExt === 'index') return '/';
  if (noExt.endsWith('/index')) return '/' + noExt.slice(0, -'/index'.length);
  return '/' + noExt;
}

function stripOverviewSuffix(title) {
  // "Acme platform overview" -> "Acme platform"
  // "Acme platform"           -> "Acme platform"
  return title.replace(/\s+overview$/i, '').trim() || title;
}

// ---------------------------------------------------------------------------
// Sidebar building
// ---------------------------------------------------------------------------

/**
 * Build a VitePress sidebar structure from the wiki manifest.
 *
 * Grouping rules:
 * - Each top-level section (from topLevelSections) becomes one sidebar group.
 * - Within a section, items preserve pageOrder.
 * - Pages whose path has 3+ components (e.g. apps/cli/tui-rendering.md) are
 *   nested under a sub-group named after the second path component.
 * - Sub-groups appear in the order they first appear in pageOrder.
 * - A section that contains a single root-level page (e.g. lore.md) is emitted
 *   as a bare sidebar link rather than a collapsible group.
 */
function buildSidebar(wikiDir, meta) {
  const pageOrder = Array.isArray(meta.pageOrder) ? meta.pageOrder : [];

  // sectionName -> [{ mdPath, text, link, subgroup? }]
  const sectionMap = new Map();
  const sectionFirstSeen = [];

  for (const mdPath of pageOrder) {
    const parts = mdPath.split('/');
    const topSection = parts[0].replace(/\.md$/, '');

    if (!sectionMap.has(topSection)) {
      sectionMap.set(topSection, []);
      sectionFirstSeen.push(topSection);
    }

    const title = readTitle(join(wikiDir, mdPath));
    const link = toLink(mdPath);
    const item = { mdPath, text: title, link };
    if (parts.length > 2) item.subgroup = parts[1];

    sectionMap.get(topSection).push(item);
  }

  // Use topLevelSections for ordering if present; otherwise fall back to first-seen order.
  let orderedSections;
  if (Array.isArray(meta.topLevelSections) && meta.topLevelSections.length > 0) {
    const known = new Set(sectionFirstSeen);
    orderedSections = [
      ...meta.topLevelSections.filter((s) => known.has(s)),
      ...sectionFirstSeen.filter((s) => !meta.topLevelSections.includes(s)),
    ];
  } else {
    orderedSections = sectionFirstSeen;
  }

  const sidebar = [];
  for (const sectionName of orderedSections) {
    const items = sectionMap.get(sectionName);

    // Single bare page (no nested items) -> top-level link, no group wrapper.
    if (items.length === 1 && !items[0].subgroup) {
      sidebar.push({ text: items[0].text, link: items[0].link });
      continue;
    }

    const groupItems = [];
    // label -> subgroup group object. Keying by label (rather than only the
    // "current" one) lets a subgroup be reopened when its items are not
    // contiguous in pageOrder, so a directory is never split across two
    // same-labeled groups.
    const subgroupByLabel = new Map();
    let sectionLink = null;
    const sectionIndexRel = `${sectionName}/index.md`;

    for (const item of items) {
      if (item.subgroup) {
        const subLabel = humanize(item.subgroup);
        let group = subgroupByLabel.get(subLabel);
        if (!group) {
          group = { text: subLabel, collapsed: false, items: [] };
          subgroupByLabel.set(subLabel, group);
          groupItems.push(group);
        }
        // Hoist a directory's own index.md onto its group as the link, instead
        // of rendering a redundant inner item ("CLI > CLI").
        const subgroupIndexRel = `${sectionName}/${item.subgroup}/index.md`;
        if (item.mdPath === subgroupIndexRel) {
          if (group.link == null) group.link = item.link;
          continue;
        }
        group.items.push({ text: item.text, link: item.link });
      } else {
        // Hoist the section's own index.md onto the section group as the link.
        if (item.mdPath === sectionIndexRel) {
          if (sectionLink == null) sectionLink = item.link;
          continue;
        }
        groupItems.push({ text: item.text, link: item.link });
      }
    }

    // A subgroup that contributed only its hoisted index becomes a bare link
    // instead of an empty collapsible.
    const normalizedGroupItems = [];
    for (const gi of groupItems) {
      if (gi.items && gi.items.length === 0) {
        if (gi.link != null) normalizedGroupItems.push({ text: gi.text, link: gi.link });
      } else {
        normalizedGroupItems.push(gi);
      }
    }

    const sectionGroup = {
      text: humanize(sectionName),
      collapsed: false,
      items: normalizedGroupItems,
    };
    if (sectionLink != null) sectionGroup.link = sectionLink;

    // A section that contributed only its hoisted index becomes a bare
    // top-level link instead of an empty collapsible.
    if (normalizedGroupItems.length === 0 && sectionLink != null) {
      sidebar.push({ text: sectionGroup.text, link: sectionLink });
    } else {
      sidebar.push(sectionGroup);
    }
  }

  return sidebar;
}

// ---------------------------------------------------------------------------
// TS serialization
// ---------------------------------------------------------------------------

/**
 * Serialize a JS value as pretty TypeScript-ish code.
 * Produces double-quoted strings, 2-space indent, no trailing commas issues.
 * Output is also valid JSON, which VitePress accepts.
 */
function serialize(value, indent = 0) {
  const pad = '  '.repeat(indent);
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    const innerPad = '  '.repeat(indent + 1);
    const lines = value.map((v) => innerPad + serialize(v, indent + 1));
    return '[\n' + lines.join(',\n') + '\n' + pad + ']';
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value);
    if (keys.length === 0) return '{}';
    const innerPad = '  '.repeat(indent + 1);
    const lines = keys.map((k) => innerPad + JSON.stringify(k) + ': ' + serialize(value[k], indent + 1));
    return '{\n' + lines.join(',\n') + '\n' + pad + '}';
  }
  return JSON.stringify(value);
}

// ---------------------------------------------------------------------------
// Output writers
// ---------------------------------------------------------------------------

const VITEPRESS_VERSION = '^1.6.0';
const MERMAID_PLUGIN_VERSION = '^2.0.17';
const MERMAID_VERSION = '^11.0.0';

function buildPackageJson() {
  return {
    name: 'wiki',
    version: '0.0.0',
    private: true,
    type: 'module',
    scripts: {
      'docs:dev': 'vitepress dev',
      'docs:build': 'vitepress build',
      'docs:preview': 'vitepress preview',
    },
    devDependencies: {
      vitepress: VITEPRESS_VERSION,
      'vitepress-plugin-mermaid': MERMAID_PLUGIN_VERSION,
      mermaid: MERMAID_VERSION,
    },
  };
}

function buildConfigTs({ title, description, sidebar }) {
  const config = {
    title,
    description: description || `${title} — generated wiki`,
    cleanUrls: true,
    lastUpdated: true,
    themeConfig: {
      nav: [{ text: 'Home', link: '/' }],
      sidebar,
      search: { provider: 'local' },
      outline: { level: [2, 3], label: 'On this page' },
      docFooter: { prev: 'Previous', next: 'Next' },
    },
  };

  return `// AUTO-GENERATED by setup-vitepress.mjs. Do not edit by hand —
// re-run the adapter after regenerating the wiki and this file will refresh
// from .wiki-meta.json. For custom theme overrides, add files under
// .vitepress/theme/ (those are preserved across adapter runs).

import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

export default withMermaid(defineConfig(${serialize(config, 0)}))
`;
}

const THEME_INDEX_TS = `// VitePress theme entry point.
//
// This file is written once by setup-vitepress.mjs and then preserved across
// adapter runs. Use it to extend the default theme: register custom Vue
// components, import custom CSS, override theme config, etc.
//
// Note: Mermaid rendering is configured by the withMermaid() wrapper in
// ../config.ts and registered automatically by vitepress-plugin-mermaid.
// You do not need to import or register Mermaid here.

import DefaultTheme from 'vitepress/theme'
import './custom.css'

export default DefaultTheme
`;

const THEME_CUSTOM_CSS = `/* Custom theme overrides. Edit freely. */
/*
:root {
  --vp-c-brand-1: #3451b2;
  --vp-c-brand-2: #3a5ccc;
}
*/
`;

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function fail(msg) {
  console.error(`${SCRIPT_NAME}: ${msg}`);
  console.error(`Run "node ${SCRIPT_NAME} --help" for usage.`);
  process.exit(1);
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    printHelp();
    process.exit(0);
  }
  if (!args.wikiDir) fail('missing <wiki-dir> argument');

  const wikiDir = args.wikiDir;
  if (!existsSync(wikiDir) || !statSync(wikiDir).isDirectory()) {
    fail(`wiki directory does not exist or is not a directory: ${wikiDir}`);
  }

  const metaPath = join(wikiDir, '.wiki-meta.json');
  if (!existsSync(metaPath)) {
    fail(`.wiki-meta.json not found in ${wikiDir}. Run the wiki skill first.`);
  }

  let meta;
  try {
    meta = JSON.parse(readFileSync(metaPath, 'utf8'));
  } catch (e) {
    fail(`could not parse ${metaPath}: ${e.message}`);
  }
  if (!Array.isArray(meta.pageOrder)) {
    fail(`${metaPath} is missing a pageOrder array`);
  }

  // Derive title from the first page in pageOrder (usually overview/index.md).
  let title = args.title;
  if (!title) {
    const firstPage = meta.pageOrder[0];
    if (firstPage) {
      const firstTitle = readTitle(join(wikiDir, firstPage));
      title = stripOverviewSuffix(firstTitle) || 'Wiki';
    } else {
      title = 'Wiki';
    }
  }
  const description = args.description || '';

  // Build sidebar.
  const sidebar = buildSidebar(wikiDir, meta);

  // Ensure .vitepress and .vitepress/theme exist.
  const vitepressDir = join(wikiDir, '.vitepress');
  const themeDir = join(vitepressDir, 'theme');
  mkdirSync(themeDir, { recursive: true });

  // Always (over)write config.ts and package.json.
  const configTs = buildConfigTs({ title, description, sidebar });
  writeFileSync(join(vitepressDir, 'config.ts'), configTs);

  const pkg = buildPackageJson();
  writeFileSync(join(wikiDir, 'package.json'), JSON.stringify(pkg, null, 2) + '\n');

  // Write theme/index.ts only if missing — preserves user customizations.
  const themeIndexPath = join(themeDir, 'index.ts');
  let themeWritten = false;
  if (!existsSync(themeIndexPath)) {
    writeFileSync(themeIndexPath, THEME_INDEX_TS);
    themeWritten = true;
  }

  // Write theme/custom.css only if missing — gives users a starting point.
  const customCssPath = join(themeDir, 'custom.css');
  let cssWritten = false;
  if (!existsSync(customCssPath)) {
    writeFileSync(customCssPath, THEME_CUSTOM_CSS);
    cssWritten = true;
  }

  // Report.
  const pageCount = meta.pageOrder.length;
  const sectionCount = sidebar.filter((s) => s.items).length;
  console.log(`VitePress configured at ${wikiDir}`);
  console.log(`  title:    ${title}`);
  console.log(`  pages:    ${pageCount}`);
  console.log(`  sections: ${sectionCount}`);
  console.log(`  config:   ${join(vitepressDir, 'config.ts')}`);
  console.log(`  theme:    ${themeIndexPath} ${themeWritten ? '(written)' : '(preserved)'}`);
  console.log(`  css:      ${customCssPath} ${cssWritten ? '(written)' : '(preserved)'}`);
  console.log(`  package:  ${join(wikiDir, 'package.json')}`);
  console.log('');
  console.log('Next steps:');
  console.log(`  cd ${wikiDir}`);
  console.log('  npm install');
  console.log('  npm run docs:dev      # live preview at http://localhost:5173');
  console.log('  npm run docs:build    # static HTML to .vitepress/dist/');
}

main();
