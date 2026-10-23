#!/usr/bin/env node
// Source AST inventory, NOT live interaction certification.
import ts from "typescript";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { relative, join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const source = join(root, "artifacts/ndsp-console/src");
const output = join(root, "docs/HUNTER_ALL_UI_CONTROLS_SOURCE_AUDIT_20261017.csv");
const summary = join(root, "docs/HUNTER_ALL_UI_CONTROLS_SOURCE_AUDIT_20261017.md");

function collect(dir) {
  const found = [];
  for (const f of readdirSync(dir, { withFileTypes: true })) {
    if (f.isDirectory()) found.push(...collect(join(dir, f.name)));
    else if (f.name.endsWith(".tsx")) found.push(join(dir, f.name));
  }
  return found.sort();
}
const rows = [];
const tagSet = new Set(["button","input","select","textarea","form","a"]);
function esc(s) { return '"' + String(s).replaceAll('"','""').replace(/[\r\n]+/g," ").slice(0,350) + '"'; }
function classify(file, tag, handler, raw) {
  if (tag === "a" && /href=/.test(raw)) return "NAVIGATION_ONLY";
  if (/disabled(?:\s|=|>)/.test(raw) && !/disabled=\{/.test(raw)) return "BLOCKED_CONTROL";
  if (/DecisionStyleSelector\.tsx$/.test(file)) return "BOT_BACKEND_PROFILE_CLIENT__E2E_PENDING";
  if (/AuthControls|AdminRegistration|AdminUsersTenants|AuthProvider|AccountEnrollment/.test(file))
    return "BACKEND_AUTH_OR_ADMIN__VERIFY_PER_ACTION";
  if (/LiveMarketPreview/.test(file)) return "READ_ONLY_MARKET__VERIFY_PER_ACTION";
  if (/ConsoleShell/.test(file)) return "NAVIGATION_OR_UI_DISPLAY";
  if (/views-trading|OperationsPreview|PreviewWorkspace|PreviewChart|Demo|SafetyPreview|ui\.tsx/.test(file))
    return "DEMO_OR_LOCAL__NO_BACKEND_ASSUMED";
  if (handler) return "HANDLER_PRESENT__BACKEND_NOT_PROVEN";
  return "NO_EXPLICIT_HANDLER__INSPECT";
}
for (const file of collect(source)) {
  const content=readFileSync(file,"utf8");
  const ast=ts.createSourceFile(file,content,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  function visit(node) {
    if ((ts.isJsxOpeningElement(node)||ts.isJsxSelfClosingElement(node))) {
      const name=node.tagName.getText(ast).toLowerCase();
      if (tagSet.has(name)) {
        const attrs=node.attributes.properties;
        let handler="";
        let label="";
        const raw=node.getText(ast);
        for (const attr of attrs) if (ts.isJsxAttribute(attr)) {
          const k=attr.name.text;
          if (/^on(Click|Change|Submit|Input|KeyDown|Blur|Focus)$/.test(k)) handler+=k+" ";
          if (["aria-label","title","type","href","name"].includes(k) && attr.initializer) label+=k+":"+attr.initializer.getText(ast).slice(0,85)+" ";
        }
        let outer=node.parent;
        let owner="-";
        while (outer && !ts.isSourceFile(outer)) {
          if (ts.isFunctionDeclaration(outer) && outer.name) { owner=outer.name.text; break; }
          if (ts.isVariableDeclaration(outer) && ts.isIdentifier(outer.name)) { owner=outer.name.text; break; }
          outer=outer.parent;
        }
        rows.push({
          file:relative(root,file),line:ast.getLineAndCharacterOfPosition(node.getStart(ast)).line+1,
          tag:name,component:owner,handler:handler.trim() || "-",label:label.trim() || "-",
          classification:classify(file,name,handler,raw),
        });
      }
    }
    ts.forEachChild(node,visit);
  }
  visit(ast);
}
const cols=["file","line","tag","component","handler","label","classification"];
writeFileSync(output,[cols.map(esc).join(","),...rows.map(r=>cols.map(k=>esc(r[k])).join(","))].join("\n")+"\n");
const grouped=Object.entries(Object.groupBy(rows,r=>r.classification))
  .sort(([a],[b])=>a.localeCompare(b)).map(([k,items])=>`| ${k} | ${items.length} |`);
writeFileSync(summary,[
 "# Hunter KSA1 UI interactive-control AST inventory (2026-10-17)",
 "",
 "This is a **source-only inventory**, not a browser E2E certification. A JSX element may be repeated by map() or hidden conditionally, and custom controls may contain additional elements. Handler presence never proves a Backend link.",
 "",
 `- Distinct interactive JSX source nodes: **${rows.length}** across **${new Set(rows.map(r=>r.file)).size}** files with controls.`,
 "- Detailed per-node file/line/handler/classification: `docs/HUNTER_ALL_UI_CONTROLS_SOURCE_AUDIT_20261017.csv`.",
 "- Backend API acceptance remains per endpoint with real-browser testing; no claim that all controls are operational.",
 "",
 "| Static category | JSX source nodes |",
 "| --- | ---: |", ...grouped,
 "",
 "Critical distinction: INVESTMENT/SPECULATIVE is now a bot-owned authenticated preference only, not signed NDSP decision mode or actual execution authority.",
].join("\n")+"\n");
console.log(`HUNTER_SOURCE_CONTROLS=${rows.length}`);
console.log(`CSV=${output}\nSUMMARY=${summary}`);
