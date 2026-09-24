import { useId, useMemo, useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import { useRepo } from "./Code.jsx";

// Build a list of what someone gets: any mix of folders, files, functions or
// classes (by name, so it follows the code), and line ranges.
export function label(it) {
  if (it.kind === "folder") return it.path ? `${it.path}/` : "everything";
  if (it.kind === "file") return it.path;
  if (it.kind === "lines") return `${it.path}, lines ${it.line_start}–${it.line_end}`;
  return `${it.symbol} in ${it.path}`;
}

export default function ItemBuilder({ files, items, onChange }) {
  const { rid } = useRepo();
  const list = useId();
  const [kind, setKind] = useState("folder");
  const [path, setPath] = useState("");
  const [syms, setSyms] = useState(null);
  const [symbol, setSymbol] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [err, setErr] = useState(null);

  const folders = useMemo(() => {
    const s = new Set();
    files.forEach((f) => f.p.split("/").slice(0, -1).forEach((_, i, parts) => s.add(parts.slice(0, i + 1).join("/"))));
    return [...s].sort();
  }, [files]);
  const options = kind === "folder" ? folders : files.map((f) => f.p);
  const isFile = files.some((f) => f.p === path);

  const loadSymbols = async (p) => {
    setSyms(null); setSymbol(""); setErr(null);
    if (!files.some((f) => f.p === p)) return;
    try {
      const d = await api.get(`/api/code/${rid}/symbols?path=${encodeURIComponent(p)}`);
      setSyms(d);
      if (!d.symbols.length && kind === "symbol") setErr("Nothing in this file has a name to pick (no functions, classes, sections or settings). Use lines instead.");
    } catch (e) { setErr(e.message); }
  };

  const add = () => {
    setErr(null);
    let it;
    if (kind === "folder") {
      if (path && !folders.includes(path)) return setErr("Pick a folder from the list.");
      it = { kind, path };
    } else if (!isFile) {
      return setErr("Pick a file from the list.");
    } else if (kind === "file") {
      it = { kind, path };
    } else if (kind === "symbol") {
      if (!symbol) return setErr("Pick one.");
      it = { kind, path, symbol };
    } else {
      const s = Number(from), e = Number(to);
      if (!(s >= 1 && e >= s && (!syms || e <= syms.lines_total))) return setErr(`Lines go from 1 to ${syms?.lines_total ?? "the end"}.`);
      it = { kind, path, line_start: s, line_end: e };
    }
    if (items.some((x) => label(x) === label(it))) return setErr("That's already in the list.");
    onChange([...items, it]);
    setSymbol(""); setFrom(""); setTo("");
  };

  return (
    <div className="ib">
      {items.length > 0 && (
        <ul className="ib-chosen">
          {items.map((it, i) => (
            <li key={i}>
              <span>{label(it)}</span>
              <button aria-label={`Remove ${label(it)}`} onClick={() => onChange(items.filter((_, j) => j !== i))}><Icon name="x" size={13} /></button>
            </li>
          ))}
        </ul>
      )}
      <div className="ib-add">
        <Seg size="sm" value={kind} onChange={(k) => { setKind(k); setErr(null); if (k === "symbol" || k === "lines") loadSymbols(path); }}
          label="What kind" options={[{ value: "folder", label: "Folder" }, { value: "file", label: "File" },
            { value: "symbol", label: "By name" }, { value: "lines", label: "Lines" }]} />
        <Field value={path} list={list} placeholder={kind === "folder" ? "core/memory (empty = everything)" : "core/memory/engine.py"}
          onChange={(e) => { setPath(e.target.value); setSyms(null); }}
          onBlur={() => (kind === "symbol" || kind === "lines") && loadSymbols(path)} aria-label="Path" />
        <datalist id={list}>{options.slice(0, 2000).map((o) => <option key={o} value={o} />)}</datalist>
        {kind === "symbol" && syms?.symbols.length > 0 && (
          <Select value={symbol} onChange={setSymbol} placeholder="Pick one"
            options={syms.symbols.map((s) => ({ value: s.name, label: `${s.name}  ·  ${s.kind}, lines ${s.start}–${s.end}` }))} />
        )}
        {kind === "lines" && (
          <div className="ib-lines">
            <Field type="number" min={1} value={from} onChange={(e) => setFrom(e.target.value)} placeholder="From" aria-label="From line" />
            <Field type="number" min={1} value={to} onChange={(e) => setTo(e.target.value)} placeholder="To" aria-label="To line" />
            {syms && <span className="t-note">of {syms.lines_total}</span>}
          </div>
        )}
        <Button size="sm" icon="plus" onClick={add}>Add</Button>
      </div>
      {err && <p className="form-error">{err}</p>}
      <p className="t-note">By name covers functions, classes, prompt sections (a capitalised heading) and settings (a CONSTANT). It's found by its name every time, so access follows it when the code moves. Lines move along with the code around them.</p>
    </div>
  );
}
