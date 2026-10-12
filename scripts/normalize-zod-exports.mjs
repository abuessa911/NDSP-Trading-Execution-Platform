import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// Orval appends a wildcard type barrel to an existing workspace entrypoint.
// Operation parameter types collide with Zod value exports. Keep types in the
// existing namespace rather than patching generated endpoint/schema files.
const path = fileURLToPath(new URL("../lib/api-zod/src/index.ts", import.meta.url));
const text = await readFile(path, "utf8");
await writeFile(path, text.replace(/^export \* from ['"]\.\/generated\/types['"];?\r?\n/gm, ""));