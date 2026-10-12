import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Deliberately dependency-free. This checks common regressions, not linguistic
// quality or all computed DOM text; the browser review covers those separately.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const preview = path.join(root, 'src/preview');
const failures = [];
let filesChecked = 0;
const catalog = fs.readFileSync(path.join(preview, 'catalog.tsx'), 'utf8');
const familyIds = [...catalog.matchAll(/\{ id: '([^']+)', slug:/g)].map((m) => m[1]);
const terms = fs.readFileSync(path.join(preview, 'terms.tsx'), 'utf8');
const translatedKeys = new Set([...terms.matchAll(/(?:['"]([^'"]+)['"]|(\w+)):\s*\{\s*en:/g)].map((m) => m[1] ?? m[2]));
const neededKeys = new Set();
for (const match of catalog.matchAll(/variants:\s*\{([^}]*)\}/g)) {
  for (const axis of match[1].matchAll(/(\w+):\s*\[/g)) neededKeys.add(axis[1]);
  for (const value of match[1].matchAll(/'([^']+)'/g)) neededKeys.add(value[1]);
}
for (const match of catalog.matchAll(/(?:sizes|states):\s*\[([^\]]*)\]/g)) {
  for (const value of match[1].matchAll(/'([^']+)'/g)) neededKeys.add(value[1]);
}
if (!familyIds.length || !neededKeys.size) failures.push('Could not inspect the static catalog; update the checker if its format changes.');
for (const key of neededKeys) if (!translatedKeys.has(key)) failures.push(`Missing localized catalog term: ${key}`);
function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? files(path.join(dir, entry.name))
      : entry.name.endsWith('.tsx') ? [path.join(dir, entry.name)] : []);
}
const brandOrStandard = /^(NAWAF(?: Design System)?|USD|EUR|SAR|PNL|KPI|Tab|Enter|Escape|Space|Home|End|X|Y)$/;
for (const file of files(preview)) {
  filesChecked++;
  const original = fs.readFileSync(file, 'utf8');
  // Code examples in template literals are intentionally not translated.
  const source = original.replace(/`(?:\\[\s\S]|[^`])*`/g, (v) => v.replace(/[^\n]/g, ' '));
  const lineAt = (index) => source.slice(0, index).split('\n').length;
  const props = /\b(label|title|placeholder|aria-label|aria-description|aria-valuetext|alt|retryLabel|closeLabel)\s*=\s*["']([^"'<>]+)["']/g;
  for (const match of source.matchAll(props)) {
    if (/[A-Za-z]{2}/.test(match[2])) {
      failures.push(`${path.relative(root, file)}:${lineAt(match.index)}: untranslated literal ${match[1]}=${JSON.stringify(match[2])}`);
    }
  }
  const text = />\s*([A-Za-z][A-Za-z0-9 /(),.:+-]*?)\s*</g;
  for (const match of source.matchAll(text)) {
    const value = match[1].trim();
    if (!/[A-Za-z]{2}/.test(value) || brandOrStandard.test(value)) continue;
    const opening = source.slice(0, match.index + 1).match(/<[^<>]+>$/)?.[0] ?? '';
    if (/^<(code|pre|kbd|samp|bdi)\b/.test(opening)) continue;
    failures.push(`${path.relative(root, file)}:${lineAt(match.index)}: untranslated JSX text ${JSON.stringify(value)}`);
  }
}
for (const locale of ['ar', 'en']) {
  const argument = process.argv.slice(2).find((v) => v.startsWith(`--${locale}=`));
  if (!argument) continue;
  const file = path.resolve(root, argument.slice(locale.length + 3));
  if (!fs.existsSync(file)) { failures.push(`Missing ${locale} guide: ${file}`); continue; }
  const html = fs.readFileSync(file, 'utf8');
  const opening = html.match(/<html\b[^>]*>/i)?.[0] ?? '';
  const dir = locale === 'ar' ? 'rtl' : 'ltr';
  if (!new RegExp(`\\blang=["']${locale}["']`, 'i').test(opening)) failures.push(`${locale} guide has incorrect html.lang`);
  if (!new RegExp(`\\bdir=["']${dir}["']`, 'i').test(opening)) failures.push(`${locale} guide has incorrect html.dir`);
  if (!/<meta\b[^>]*charset=["']?utf-8/i.test(html)) failures.push(`${locale} guide lacks UTF-8 charset`);
  if (!/<style[\s>]/i.test(html)) failures.push(`${locale} guide lacks self-contained CSS`);
  if (/<script\b[^>]*src=|<link\b[^>]*rel=["']stylesheet/i.test(html)) failures.push(`${locale} guide depends on external scripts/styles`);
  if (!/dir=["']ltr["']/i.test(html)) failures.push(`${locale} guide lacks isolated technical/code direction`);
  const size = Buffer.byteLength(html);
  for (const id of familyIds) {
    if (!html.includes(`id="family-${id}"`)) failures.push(`${locale} guide is missing the ${id} family chapter`);
  }
  console.log(`${locale.toUpperCase()} guide: ${(size / 1024).toFixed(1)} KiB, lang=${locale}, dir=${dir}`);
}
if (failures.length) {
  console.error(`Localization regression check: ${failures.length} finding(s) in ${filesChecked} preview modules.`);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} else {
  console.log(`Localization regression check passed: ${filesChecked} preview modules, ${neededKeys.size} catalog terms, ${familyIds.length} families.`);
}
