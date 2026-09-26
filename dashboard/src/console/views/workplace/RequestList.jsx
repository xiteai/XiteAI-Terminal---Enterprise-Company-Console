import { Status } from "../../../components/Badge.jsx";
import Button from "../../../components/Button.jsx";
import Empty from "../../../components/Empty.jsx";
import { date } from "../../../lib/format.js";
import { STATUS_LABEL, STATUS_TONE, amount, detail, rupees } from "./labels.js";

// Leave, expenses and asset requests are one thing on the server and read as
// one thing here: who, what, how much, where it got to. `onWithdraw` appears
// on your own pending rows, `onDecide` on rows you're being asked to decide.
export default function RequestList({ items, showWho = false, onWithdraw, onDecide, empty }) {
  if (!items.length) return <Empty title={empty} />;
  return (
    <div className="table">
      <table>
        <thead>
          <tr>
            {showWho && <th>Who</th>}
            <th>What</th>
            <th>When</th>
            <th className="r">Amount</th>
            <th>Status</th>
            <th>Filed</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id}>
              {showWho && (
                <td className="strong">
                  {r.staff?.name || "—"}
                  {r.staff?.title && <span className="wp-sub"> · {r.staff.title}</span>}
                </td>
              )}
              <td className="strong">{r.title}</td>
              <td className="tnum">{detail(r)}</td>
              <td className="r tnum">{amount(r)}</td>
              <td>
                <Status tone={STATUS_TONE[r.status]}>{STATUS_LABEL[r.status]}</Status>
                {r.decided_by && <span className="wp-sub"> by {r.decided_by.name}</span>}
                {r.fine_paise > 0 && <span className="wp-fine"> · {rupees(r.fine_paise)} fine</span>}
              </td>
              <td className="tnum">{date(r.created_at)}</td>
              <td className="r">
                {onDecide && r.status === "pending" && (
                  <div className="wp-actions">
                    <Button size="sm" onClick={() => onDecide(r, true)}>Approve</Button>
                    <Button size="sm" variant="quiet" onClick={() => onDecide(r, false)}>Decline</Button>
                  </div>
                )}
                {onWithdraw && r.status === "pending" && (
                  <Button size="sm" variant="quiet" onClick={() => onWithdraw(r)}>Withdraw</Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
