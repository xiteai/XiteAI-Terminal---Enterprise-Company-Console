import { useState } from "react";
import Card from "../components/Card.jsx";
import "./charts.css";

// A chart section, with its table twin one click away: the same numbers,
// readable without a mouse or colour vision. `table` is [{label, value}] or rows.
export default function ChartCard({ title, subtitle, table, columns = ["", "Value"], children, className, extra }) {
  const [asTable, setAsTable] = useState(false);
  return (
    <Card
      title={title}
      subtitle={subtitle}
      className={className}
      action={
        <>
          {extra}
          {table && (
            <button className={`viz-toggle ${asTable ? "on" : ""}`} onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}>
              {asTable ? "Chart" : "Table"}
            </button>
          )}
        </>
      }
    >
      {asTable && table ? (
        <div className="viz-table-wrap">
          <table className="viz-table">
            <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {table.map((row, i) => (
                <tr key={i}>
                  {(Array.isArray(row) ? row : [row.label, row.value]).map((cell, j) => (
                    <td key={j} className={j ? "tnum" : undefined}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        children
      )}
    </Card>
  );
}
