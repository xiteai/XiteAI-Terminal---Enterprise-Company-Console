import { useState } from "react";
import { api, qs } from "../../../lib/api.js";
import { compact, date } from "../../../lib/format.js";
import { useProduct } from "../../../lib/product.jsx";
import { useSession } from "../../../lib/session.jsx";
import { useData } from "../../../lib/useData.js";
import BarList from "../../../charts/BarList.jsx";
import ChartCard from "../../../charts/ChartCard.jsx";
import LineChart from "../../../charts/LineChart.jsx";
import StatTile from "../../../charts/StatTile.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import EntryModal from "./EntryModal.jsx";
import { monthLabel, rupees, rupeesCompact } from "./labels.js";
import "./Finance.css";

// Everything financial for one product: what came in, what went out, and the
// P&L between them. Entered by hand — there's no billing system plugged in
// yet — the way a payslip is issued by hand.
export default function Finance() {
  const { slug, product } = useProduct();
  const { can } = useSession();
  const manage = can("finance.manage");
  const summary = useData(() => api.get(`/api/finance/summary${qs({ product: slug })}`), [slug]);
  const log = useData(() => api.get(`/api/finance${qs({ product: slug })}`), [slug]);
  const options = useData(() => api.get("/api/finance/options"), []);
  const [adding, setAdding] = useState(false);

  const s = summary.data;
  const entries = log.data?.items || [];

  const netPoints = (s?.months || []).map((m) => ({ date: `${m.period}-01`, value: m.net_paise / 100 }));

  const remove = async (id) => {
    await api.del(`/api/finance/${id}${qs({ product: slug })}`);
    summary.reload();
    log.reload();
  };

  return (
    <div className="stack">
      <PageHeader title="Finance" subtitle={`Revenue and cost for ${product?.name || "this product"}.`}>
        {manage && <Button variant="primary" icon="plus" onClick={() => setAdding(true)}>Log entry</Button>}
      </PageHeader>

      <ErrorNote error={summary.error} onRetry={summary.reload} />

      {s && (
        <>
          <div className="kpis">
            <StatTile label="Revenue" value={rupeesCompact(s.revenue_paise)} note="last 12 months" />
            <StatTile label="Cost" value={rupeesCompact(s.cost_paise)} note="last 12 months" />
            <StatTile label="Net" value={rupeesCompact(s.net_paise)} note={s.net_paise >= 0 ? "in the black" : "in the red"} />
            <StatTile label="Margin" value={s.margin === null ? "–" : `${(s.margin * 100).toFixed(0)}%`} note="net of revenue" />
          </div>

          <ChartCard title="Net, month by month" subtitle="Revenue minus cost"
            table={(s.months || []).map((m) => [monthLabel(m.period), rupees(m.net_paise)])} columns={["Month", "Net"]}>
            <LineChart points={netPoints} label="Net" format={(v) => rupeesCompact(v * 100)} />
          </ChartCard>

          <div className="grid-2">
            <Card title="Revenue by category">
              <BarList items={(s.by_category.revenue || []).map((c) => ({ label: c.label, value: c.amount_paise / 100 }))}
                format={(v) => `₹${compact(v)}`} empty="No revenue logged yet." />
            </Card>
            <Card title="Cost by category">
              <BarList items={(s.by_category.cost || []).map((c) => ({ label: c.label, value: c.amount_paise / 100 }))}
                format={(v) => `₹${compact(v)}`} empty="No cost logged yet." />
            </Card>
          </div>
        </>
      )}

      <Card title="Log" flush>
        <ErrorNote error={log.error} onRetry={log.reload} />
        {entries.length === 0 ? <Empty title="Nothing logged yet." /> : (
          <div className="table">
            <table>
              <thead>
                <tr><th>Kind</th><th>Category</th><th>Note</th><th className="r">Amount</th><th>Date</th><th>By</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td><span className={`fin-kind fin-${e.kind}`}>{e.kind === "revenue" ? "Revenue" : "Cost"}</span></td>
                    <td className="strong">{e.category_label}</td>
                    <td className="wp-sub">{e.note || "—"}</td>
                    <td className="r tnum">{rupees(e.amount_paise)}</td>
                    <td className="tnum">{date(e.occurred_on)}</td>
                    <td className="wp-sub">{e.created_by?.name || "—"}</td>
                    <td className="r">
                      {manage && (
                        <button type="button" className="fin-del" onClick={() => remove(e.id)} aria-label="Delete entry">
                          <Icon name="trash" size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <EntryModal open={adding} options={options.data} onClose={() => setAdding(false)}
        onDone={() => { setAdding(false); summary.reload(); log.reload(); }} />
    </div>
  );
}
