#!/usr/bin/env node
/** Static audit of app-owned controls, excluding generic component library. */
import fs from "node:fs";
import path from "node:path";
import {createRequire} from "node:module";
const app="/opt/hunter_ksa1-bot/artifacts/ndsp-console";
const req=createRequire(app+"/package.json");
const ts=req("typescript");
const root=app+"/src";
const controls=[];
function walkFiles(dir){
 for(const item of fs.readdirSync(dir,{withFileTypes:true})){
   const abs=path.join(dir,item.name);
   if(item.isDirectory()) {
     if(abs.endsWith("/components/ui")||item.name==="__tests__")continue;
     walkFiles(abs);
   }else if(item.name.endsWith(".tsx"))visit(abs);
 }
}
function visit(file){
 const source=fs.readFileSync(file,"utf8");
 const tree=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 function visitNode(node){
   if(ts.isJsxOpeningElement(node)||ts.isJsxSelfClosingElement(node)){
     const tag=node.tagName.getText(tree);
     if(tag==="button"||tag==="Button"||tag==="Link"||tag==="input"||tag==="select"){
       const attrs=new Map();
       for(const p of node.attributes.properties){
         if(ts.isJsxAttribute(p))attrs.set(p.name.getText(tree),p.initializer?.getText(tree)??"");
       }
       const loc=tree.getLineAndCharacterOfPosition(node.getStart());
       const disabled=attrs.has("disabled") ? (attrs.get("disabled")||"always") : "";
       controls.push({file:path.relative(root,file),line:loc.line+1,tag,
         action:attrs.has("onClick")?"onClick":attrs.has("onChange")?"onChange":
           attrs.has("onSubmit")?"onSubmit":attrs.get("type")==='"submit"'?"submit":
           attrs.has("href")?"navigation":"none",
         disabled, name:source.slice(node.getStart(),Math.min(source.length,node.getStart()+160)).replace(/\s+/g," ").slice(0,110)});
     }
   }
   ts.forEachChild(node,visitNode);
 }
 visitNode(tree);
}
walkFiles(root);
const buttons=controls.filter(x=>x.tag==="button"||x.tag==="Button");
const disabled=buttons.filter(x=>x.disabled);
const inert=buttons.filter(x=>!x.disabled&&x.action==="none");
const temporary=buttons.filter(x=>x.disabled&&x.disabled!=="always");
const report=[
 "# hunter_ksa1 — Frontend control static inventory",
 "Date: 2026-10-16 (static inspection; not browser acceptance)",
 "",
 "- Total app-owned button instances: "+buttons.length,
 "- Button instances with permanent disabled attribute: "+disabled.filter(x=>x.disabled==="always").length,
 "- Button instances with conditional disabled attribute: "+temporary.length,
 "- Buttons lacking direct onClick/submit handler (may rely on wrapping forms): "+inert.length,
 "- Input and select instances: "+controls.filter(x=>x.tag==="input"||x.tag==="select").length,
 "- Navigation Link instances: "+controls.filter(x=>x.tag==="Link").length,
 "",
 "## Permanently unavailable buttons (intentional gates)",
 ...disabled.filter(x=>x.disabled==="always").map(x=>"- "+x.file+":"+x.line+" — "+x.name),
 "",
 "## Buttons with no direct action",
 ...inert.map(x=>"- "+x.file+":"+x.line+" — "+x.name),
 "",
 "## Implementation status",
 "- Browser-only: display preferences, preview bot settings, market watchlist favorites, preview alert read/acknowledge, filters, simulated manual/automatic selection and mode appearance.",
 "- Private M1 backend: readiness, directory/audit and protected invitation registration (requires admin MFA and valid session).",
 "- Not publicly wired: browser OIDC login, admin registration, user session/cookies. Production gateway does not route /api or /oidc.",
 "- Deliberately blocked: real Binance orders, autonomous trading, replay engine, private exchange configuration.",
 "- This is a control-level source inventory; successful rendering and click behavior must be verified separately in a browser."
].join("\n")+"\n";
const file="/opt/hunter_ksa1-bot/docs/HUNTER_UI_CONTROLS_AUDIT_20261016.md";
fs.writeFileSync(file,report);
console.log(report.slice(0,9000));
