import Icon from "./Icon.jsx";
import "./DetailList.css";

// Label / value rows. Values that are empty are skipped, so a partial profile
// never shows a column of dashes.
export default function DetailList({ items, columns = 1 }) {
  const rows = items.filter((it) => it && it.value !== undefined && it.value !== null && it.value !== "" && it.value !== false);
  if (!rows.length) return null;
  return (
    <dl className="details" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
      {rows.map((it) => (
        <div className="details-row" key={it.label}>
          <dt>{it.icon && <Icon name={it.icon} size={14} />}{it.label}</dt>
          <dd className={it.mono ? "mono" : undefined}>{it.value}</dd>
        </div>
      ))}
    </dl>
  );
}
