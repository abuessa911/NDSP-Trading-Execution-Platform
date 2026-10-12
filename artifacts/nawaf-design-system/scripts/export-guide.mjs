// Generates public/guides/nawaf-guide-{en,ar}.html from the SAME content module the in-app guide renders.
import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const tsx = resolve(root, 'node_modules/.bin/tsx');
const r = spawnSync(tsx, ['--tsconfig', resolve(root, 'scripts/tsconfig.guide.json'), resolve(root, 'src/preview/guide/export-entry.tsx'), resolve(root, 'public/guides')], { stdio: 'inherit', cwd: root });
process.exit(r.status ?? 1);
