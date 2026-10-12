"use client";
import { useCallback, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { Tx, Drawer } from "./ui";

export default function SafetyPreview() {
  const [open, setOpen] = useState(false);
  const [phrase, setPhrase] = useState("");
  const [stopped, setStopped] = useState(false);
  const close = useCallback(() => { setOpen(false); setPhrase(""); }, []);
  return <section className="panel emergency-preview">
    <div className="row"><h2><ShieldAlert size={17} aria-hidden /> <Tx>{"Emergency protection concept"}</Tx></h2><span className="demo-tag"><Tx>{"DESIGN ONLY"}</Tx></span></div>
    <p className="notice" role="status"><Tx>{stopped ? "DEMO STOP DISPLAYED. No command was sent and no real system changed." : "Real execution is unavailable. This previews the deliberate interaction for a future emergency control."}</Tx></p>
    <div className="demo-actions"><button className="button danger" onClick={() => setOpen(true)}><Tx>{"Preview emergency confirmation"}</Tx></button>
      {stopped && <button className="button" onClick={() => setStopped(false)}><Tx>{"Reset preview"}</Tx></button>}</div>
    {open && <Drawer title="Emergency stop — visual preview only" onClose={close}>
      <p><Tx>{"No exchange, worker or execution engine will receive this action. This is not a working safety control."}</Tx></p>
      <form onSubmit={event => { event.preventDefault(); if (phrase !== "PREVIEW STOP") return; setStopped(true); close(); }}>
        <label className="field"><span><Tx>{"Type PREVIEW STOP to display the demo stopped state"}</Tx></span><input autoComplete="off" value={phrase} onChange={event => setPhrase(event.target.value)} data-testid="preview-stop-phrase" /></label>
        <button className="button danger" type="submit" disabled={phrase !== "PREVIEW STOP"}><Tx>{"Display demo stopped state"}</Tx></button>
      </form>
    </Drawer>}
  </section>;
}
