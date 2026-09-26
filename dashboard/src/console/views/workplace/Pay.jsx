import { api } from "../../../lib/api.js";
import { date } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import { rupees } from "./labels.js";

const month = (period) =>
  new Date(`${period}-01T00:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" });

// Your payslips. Someone else's needs pay.all and a level above theirs, which
// the server checks — this page only ever asks for your own.
export default function Pay() {
  const slips = useData(() => api.get("/api/workplace/payslips"), []);
  const items = slips.data?.items || [];

  return (
    <div className="stack">
      <PageHeader title="Pay" subtitle="What you were paid, month by month." />
      <Card flush>
        <ErrorNote error={slips.error} onRetry={slips.reload} />
        {items.length === 0 ? (
          <Empty title="No payslips yet">Payroll hasn't issued one for you.</Empty>
        ) : (
          <div className="table">
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th className="r">Gross</th>
                  <th className="r">Deductions</th>
                  <th className="r">Net</th>
                  <th>Issued</th>
                </tr>
              </thead>
              <tbody>
                {items.map((s) => (
                  <tr key={s.id}>
                    <td className="strong">{month(s.period)}</td>
                    <td className="r tnum">{rupees(s.gross_paise)}</td>
                    <td className="r tnum">{rupees(s.deductions_paise)}</td>
                    <td className="r tnum strong">{rupees(s.net_paise)}</td>
                    <td className="tnum">{date(s.issued_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
