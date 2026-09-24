import { useEffect, useMemo, useState } from "react";
import { cx } from "../../../lib/cx.js";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";

// The folder map. Every file shows (with the map permission); what each one
// holds for you is a word on the right: edit, read, part, or a lock.
function build(files) {
  const root = { name: "", path: "", dirs: new Map(), files: [] };
  for (const f of files) {
    const parts = f.p.split("/");
    let node = root;
    parts.slice(0, -1).forEach((part, i) => {
      if (!node.dirs.has(part)) node.dirs.set(part, { name: part, path: parts.slice(0, i + 1).join("/"), dirs: new Map(), files: [] });
      node = node.dirs.get(part);
    });
    node.files.push({ ...f, name: parts[parts.length - 1] });
  }
  return root;
}

const WORD = { full: "read", partial: "part" };

function Mark({ f }) {
  if (f.a === "none") {
    return <Icon name={f.k ? "access" : "lock"} size={12} className="tr-lock" title={f.k ? "Protected: the founder's" : "Not shared with you"} />;
  }
  return (
    <span className={cx("tr-mark", f.e && "edit")}>
      {f.k && <Icon name="access" size={11} className="tr-shield" title="Protected" />}
      {f.e ? "edit" : WORD[f.a]}
    </span>
  );
}

function Dir({ node, depth, open, toggle, selected, onSelect }) {
  const dirs = [...node.dirs.values()].sort((a, b) => a.name.localeCompare(b.name));
  const files = [...node.files].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <>
      {dirs.map((d) => (
        <div key={d.path}>
          <button className="tr-row tr-dir" style={{ paddingLeft: 8 + depth * 14 }} onClick={() => toggle(d.path)}
            aria-expanded={open.has(d.path)}>
            <Icon name={open.has(d.path) ? "chevronDown" : "chevronRight"} size={12} />
            <span className="tr-name">{d.name}</span>
          </button>
          {open.has(d.path) && <Dir node={d} depth={depth + 1} open={open} toggle={toggle} selected={selected} onSelect={onSelect} />}
        </div>
      ))}
      {files.map((f) => (
        <button key={f.p} className={cx("tr-row tr-file", f.p === selected && "on", f.a === "none" && "locked")}
          style={{ paddingLeft: 22 + depth * 14 }} onClick={() => onSelect(f)} title={f.p}>
          <span className="tr-name">{f.name}</span>
          <Mark f={f} />
        </button>
      ))}
    </>
  );
}

export default function Tree({ files, selected, onSelect }) {
  const root = useMemo(() => build(files), [files]);
  const [open, setOpen] = useState(() => new Set());
  const [q, setQ] = useState("");
  const [mine, setMine] = useState(false);

  // Open the folders leading to the selected file.
  useEffect(() => {
    if (!selected) return;
    setOpen((o) => {
      const next = new Set(o);
      selected.split("/").slice(0, -1).forEach((_, i, parts) => next.add(parts.slice(0, i + 1).join("/")));
      return next;
    });
  }, [selected]);

  const toggle = (p) => setOpen((o) => { const n = new Set(o); if (n.has(p)) n.delete(p); else n.add(p); return n; });
  const needle = q.trim().toLowerCase();
  const flat = needle || mine
    ? files.filter((f) => (!needle || f.p.toLowerCase().includes(needle)) && (!mine || f.a !== "none")).slice(0, 300)
    : null;
  const count = files.filter((f) => f.a !== "none").length;

  return (
    <div className="tr">
      <div className="tr-tools">
        <Field icon="search" placeholder="Find a file" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Find a file" />
        <button className={cx("tr-mine", mine && "on")} onClick={() => setMine((m) => !m)} aria-pressed={mine}>
          Only mine <span className="tnum">{count}</span>
        </button>
      </div>
      <div className="tr-list scroll-y">
        {files.length === 0 && <p className="t-note tr-empty">Nothing here is shared with you yet.</p>}
        {flat
          ? flat.map((f) => (
            <button key={f.p} className={cx("tr-row tr-file", f.p === selected && "on", f.a === "none" && "locked")}
              onClick={() => onSelect(f)} title={f.p}>
              <span className="tr-name">{f.p}</span>
              <Mark f={f} />
            </button>
          ))
          : <Dir node={root} depth={0} open={open} toggle={toggle} selected={selected} onSelect={onSelect} />}
      </div>
    </div>
  );
}
