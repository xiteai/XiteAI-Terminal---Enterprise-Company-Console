import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { useDebounced } from "../../../lib/useData.js";
import { cx } from "../../../lib/cx.js";
import Icon from "../../../components/Icon.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useRepo } from "./Code.jsx";

// Search the way a chat app does: type, and every line that says it appears,
// grouped by file, with the function or prompt section it sits in. The server
// only ever returns lines this person may see.
function Highlight({ text, needle }) {
  if (!needle) return text;
  const parts = text.split(new RegExp(`(${needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig"));
  return parts.map((p, i) => (i % 2 ? <mark key={i}>{p}</mark> : <Fragment key={i}>{p}</Fragment>));
}

const KIND = { function: "fn", class: "class", section: "section", setting: "setting" };

export default function Search() {
  const { rid, giveAccess } = useRepo();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [active, setActive] = useState(0);
  const box = useRef(null);
  const input = useRef(null);
  const needle = useDebounced(q.trim(), 200);

  useEffect(() => {
    if (needle.length < 2) { setRes(null); setErr(null); return undefined; }
    let alive = true;
    setBusy(true);
    api.get(`/api/code/${rid}/search${qs({ q: needle })}`)
      .then((d) => { if (alive) { setRes(d); setErr(null); setActive(0); } })
      .catch((e) => alive && setErr(e.message))
      .finally(() => alive && setBusy(false));
    return () => { alive = false; };
  }, [needle, rid]);

  // "/" anywhere on the page puts you in the search box; a click outside closes it.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        input.current?.focus();
      }
    };
    const onDown = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("mousedown", onDown); };
  }, []);

  const groups = useMemo(() => {
    const byPath = new Map();
    (res?.hits || []).forEach((h) => {
      if (!byPath.has(h.path)) byPath.set(h.path, []);
      byPath.get(h.path).push(h);
    });
    return [...byPath.entries()];
  }, [res]);
  const flat = useMemo(() => [
    ...(res?.files || []).filter((f) => f.access !== "none").map((f) => ({ path: f.path, line: null })),
    ...groups.flatMap(([, hits]) => hits.map((h) => ({ path: h.path, line: h.line }))),
  ], [res, groups]);

  const openAt = (path, line) => {
    setOpen(false);
    navigate(`/console/code${qs({ path, line: line || undefined })}`);
  };
  const onKey = (e) => {
    if (e.key === "Escape") { setOpen(false); input.current?.blur(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, flat.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter" && flat[active]) { openAt(flat[active].path, flat[active].line); }
  };

  let idx = -1;
  const total = res ? res.hits.length : 0;
  return (
    <div className="cs" ref={box}>
      <label className="cs-box">
        <Icon name="search" size={16} />
        <input ref={input} value={q} placeholder="Search code, functions, prompt sections and file names" aria-label="Search the codebase"
          onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)} onKeyDown={onKey} />
        {busy ? <Spinner size={14} /> : <kbd>/</kbd>}
      </label>
      {open && needle.length >= 2 && (
        <div className="cs-panel scroll-y" role="listbox" aria-label="Search results">
          {err && <p className="form-error cs-note">{err}</p>}
          {res && !err && (
            <p className="cs-note">
              {total === 0 && res.files.length === 0 ? `Nothing you can see says “${res.q}”.`
                : `${total}${res.more ? "+" : ""} line${total === 1 ? "" : "s"} in ${groups.length} file${groups.length === 1 ? "" : "s"}`
                  + (res.files.length ? `, ${res.files.length} file name${res.files.length === 1 ? "" : "s"}` : "")}
              <span className="faint"> · {(res.ms / 1000).toFixed(2)}s</span>
            </p>
          )}
          {res?.files.length > 0 && (
            <div className="cs-group">
              <p className="cs-head">File names</p>
              {res.files.map((f) => {
                const mine = f.access !== "none";
                if (mine) idx += 1;
                const me = idx;
                return (
                  <button key={f.path} className={cx("cs-row", mine && me === active && "on", !mine && "locked")} disabled={!mine}
                    onClick={() => openAt(f.path)} onMouseEnter={() => mine && setActive(me)}>
                    <Icon name={mine ? "file" : "lock"} size={13} />
                    <span className="cs-path"><Highlight text={f.path} needle={res.q} /></span>
                    {f.protected && <span className="cs-kind">protected</span>}
                  </button>
                );
              })}
            </div>
          )}
          {groups.map(([path, hits]) => (
            <div key={path} className="cs-group">
              <div className="cs-head">
                <button className="cs-file" onClick={() => openAt(path)}>{path}</button>
                <span className="faint">{hits.length}</span>
                {giveAccess && (
                  <button className="text-link cs-give" onClick={() => {
                    setOpen(false);
                    const named = hits.find((h) => h.symbol && h.symbol.kind !== "class")?.symbol;
                    giveAccess([named ? { kind: "symbol", path, symbol: named.name } : { kind: "file", path }]);
                  }}>Give access</button>
                )}
              </div>
              {hits.map((h) => {
                idx += 1;
                const me = idx;
                return (
                  <button key={`${h.line}`} className={cx("cs-row", me === active && "on")} onClick={() => openAt(path, h.line)}
                    onMouseEnter={() => setActive(me)}>
                    <span className="cs-line tnum">{h.line}</span>
                    {h.symbol && <span className="cs-kind" title={h.symbol.kind}>{KIND[h.symbol.kind] || h.symbol.kind} {h.symbol.name}</span>}
                    <code className="cs-text"><Highlight text={h.text} needle={res.q} /></code>
                  </button>
                );
              })}
            </div>
          ))}
          {res?.more && <p className="cs-note faint">Showing the first matches. Add a word to narrow it down.</p>}
        </div>
      )}
    </div>
  );
}
