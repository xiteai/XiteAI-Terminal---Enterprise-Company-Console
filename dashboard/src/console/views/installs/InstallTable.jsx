import { ago } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import { cx } from "../../../lib/cx.js";
import { Status } from "../../../components/Badge.jsx";
import Empty from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import { health, statusTone } from "./health.js";

function Th({ label, k, sortable, sort, onSort, className }) {
  if (!k || !sortable.includes(k)) return <th className={className}>{label}</th>;
  const on = sort.key === k;
  return (
    <th className={className} aria-sort={on ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}>
      <button className={cx("th-sort", on && "on")} onClick={() => onSort(k)}>
        {label}
        <Icon name={on && sort.dir === "asc" ? "chevronUp" : "chevronDown"} size={12} />
      </button>
    </th>
  );
}

// Columns appear only when the viewer's level can see what's in them.
export default function InstallTable({ items, sortable, sort, onSort, latest, onOpen }) {
  const { product } = useProduct();
  const w = words(product);
  if (!items.length) return <Empty title={`No ${w.many} match.`}>Try clearing the search or the filters.</Empty>;
  const showName = items.some((i) => "name" in i.person);
  const showAge = items.some((i) => "age" in i.person || "age_band" in i.person);
  const showRegion = items.some((i) => "region" in i);
  const th = { sortable, sort, onSort };
  return (
    <div className="table">
      <table>
        <thead>
          <tr>
            <Th label="Code" k="code" {...th} />
            {showName && <Th label="Person" k="name" {...th} />}
            {showAge && <Th label="Age" k="age" {...th} />}
            <Th label="Version" k="version" {...th} />
            <th>{w.os}</th>
            {showRegion && <th>Region</th>}
            <Th label="Last seen" k="last_seen" {...th} />
            <th>Health</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => {
            const h = health(i);
            return (
              <tr key={i.id} className="row-link" tabIndex={0} onClick={() => onOpen(i)} onKeyDown={(e) => e.key === "Enter" && onOpen(i)}>
                <td className="mono">{i.code}{i.is_demo && <span className="demo-tag">Demo</span>}</td>
                {showName && <td>{i.person.name || <span className="muted">{i.person.consented ? "–" : "Not shared"}</span>}</td>}
                {showAge && <td className="tnum">{i.person.age ?? i.person.age_band ?? <span className="muted">–</span>}</td>}
                <td className="tnum">
                  {i.app_version}
                  {latest && i.app_version !== latest && <span className="in-behind">behind</span>}
                </td>
                <td className="muted">{i.os_version}</td>
                {showRegion && <td className="muted">{i.region || "–"}</td>}
                <td className="muted">{ago(i.last_seen)}</td>
                <td><Status tone={statusTone(h.tone)}>{h.label}</Status></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
