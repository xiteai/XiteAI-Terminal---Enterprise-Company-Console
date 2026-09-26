import { useMemo, useState } from "react";
import { api } from "../../../lib/api.js";
import { date } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import { Status } from "../../../components/Badge.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Select from "../../../components/Select.jsx";
import LeaveCalendar from "./LeaveCalendar.jsx";
import { STATUS_LABEL, STATUS_TONE } from "./labels.js";
import RequestList from "./RequestList.jsx";

const todayIso = () => new Date().toISOString().slice(0, 10);
const startOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);

// Your leave, built around the thing you actually think in: a calendar, not
// two date fields. Click a day to pick it, click it again to drop it — leave
// doesn't always come in a straight run, and now neither does this.
export default function Leave() {
  const opts = useData(() => api.get("/api/workplace/options"), []);
  const balance = useData(() => api.get("/api/workplace/leave/balance"), []);
  const mine = useData(() => api.get("/api/workplace/requests?kind=leave"), []);
  const [month, setMonth] = useState(startOfMonth(new Date()));
  const holidayList = useData(() => api.get(`/api/workplace/leave/holidays?year=${month.getFullYear()}`), [month.getFullYear()]);
  const [leaveType, setLeaveType] = useState("annual");
  const [selected, setSelected] = useState(new Set());
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [addingHoliday, setAddingHoliday] = useState(false);
  const [holidayForm, setHolidayForm] = useState({ date: "", label: "" });

  const items = mine.data?.items || [];
  const holidayMap = useMemo(() => Object.fromEntries((holidayList.data?.items || []).map((h) => [h.date, h.label])), [holidayList.data]);
  const canManageHolidays = holidayList.data?.can_manage;

  const upcoming = useMemo(() => items
    .filter((r) => r.status !== "withdrawn" && r.status !== "declined" && r.end_date >= todayIso())
    .sort((a, b) => a.start_date.localeCompare(b.start_date)), [items]);

  const shiftMonth = (delta, toToday) => setMonth((m) => (toToday ? startOfMonth(new Date())
    : new Date(m.getFullYear(), m.getMonth() + delta, 1)));

  const toggle = (day) => setSelected((s) => {
    const next = new Set(s);
    if (next.has(day)) next.delete(day); else next.add(day);
    return next;
  });

  const dates = [...selected].sort();

  const submit = async () => {
    if (!dates.length) { setError({ message: "Pick at least one day on the calendar first." }); return; }
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/workplace/requests/leave", { leave_type: leaveType, dates, note });
      setSelected(new Set());
      setNote("");
      balance.reload();
      mine.reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async (r) => {
    await api.post(`/api/workplace/requests/${r.id}/withdraw`);
    balance.reload();
    mine.reload();
  };

  const addHoliday = async () => {
    try {
      await api.post("/api/workplace/leave/holidays", holidayForm);
      setHolidayForm({ date: "", label: "" });
      setAddingHoliday(false);
      holidayList.reload();
    } catch (e) {
      setError(e);
    }
  };

  const removeHoliday = async (id) => {
    await api.del(`/api/workplace/leave/holidays/${id}`);
    holidayList.reload();
  };

  const typeOptions = Object.entries(opts.data?.leave_types || {}).map(([value, label]) => ({ value, label }));

  return (
    <div className="stack">
      <PageHeader title="Leave" subtitle="What you have left, and what you've asked for." />

      <ErrorNote error={balance.error} onRetry={balance.reload} />
      <div className="wp-stats">
        {(balance.data?.types || []).map((t) => (
          <div key={t.key} className="wp-stat">
            <span className="wp-stat-n tnum">{t.left === null ? "–" : t.left}</span>
            <span className="wp-stat-l">{t.label}</span>
            <span className="wp-stat-s">
              {t.entitled === null ? "No limit" : `${t.taken} of ${t.entitled} used`}
            </span>
          </div>
        ))}
      </div>

      <div className="lc-layout">
        <Card flush className="lc-card">
          <LeaveCalendar
            month={month}
            onMonth={shiftMonth}
            requests={items}
            holidayMap={holidayMap}
            selected={selected}
            onToggle={toggle}
            minIso={leaveType === "annual" ? todayIso() : undefined}
          />
          {canManageHolidays && (
            <div className="lc-holidays">
              <div className="lc-holidays-head">
                <span>Holidays this year</span>
                <button type="button" className="lc-add" onClick={() => setAddingHoliday((v) => !v)}>
                  <Icon name="plus" size={13} />Add
                </button>
              </div>
              {addingHoliday && (
                <div className="lc-holiday-form">
                  <Field type="date" value={holidayForm.date} onChange={(e) => setHolidayForm((f) => ({ ...f, date: e.target.value }))} />
                  <Field placeholder="Diwali" value={holidayForm.label} onChange={(e) => setHolidayForm((f) => ({ ...f, label: e.target.value }))} />
                  <Button size="sm" variant="primary" onClick={addHoliday}>Save</Button>
                </div>
              )}
              <ul className="lc-holiday-list">
                {(holidayList.data?.items || []).map((h) => (
                  <li key={h.id}>
                    <span>{date(h.date, { day: "numeric", month: "short" })}</span>
                    <span className="lc-holiday-label">{h.label}</span>
                    <button type="button" onClick={() => removeHoliday(h.id)} aria-label={`Remove ${h.label}`}><Icon name="x" size={13} /></button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>

        <div className="lc-side">
          <Card title="Apply">
            <div className="wp-fields">
              <Select label="Kind" value={leaveType} onChange={setLeaveType} options={typeOptions} />
              <Field label="Picked" value={dates.length ? `${dates.length} day${dates.length === 1 ? "" : "s"}` : "None yet"} disabled />
            </div>
            <div style={{ marginTop: 12 }}>
              <Field label="Note" hint="Optional" value={note} onChange={(e) => setNote(e.target.value)}
                placeholder="Anything your manager should know" />
            </div>
            <ErrorNote error={error} />
            <div className="wp-submit" style={{ marginTop: 12 }}>
              {dates.length > 0 && <Button variant="quiet" onClick={() => setSelected(new Set())}>Clear</Button>}
              <Button variant="primary" busy={busy} onClick={submit}>Send for approval</Button>
            </div>
          </Card>

          <Card title="Upcoming" subtitle={upcoming.length ? `${upcoming.length} on the books` : undefined}>
            {upcoming.length === 0 ? <Empty title="Nothing coming up." /> : (
              <ul className="lc-upcoming">
                {upcoming.map((r) => (
                  <li key={r.id}>
                    <span className="lc-up-when">
                      <b>{date(r.start_date, { day: "numeric", month: "short" })}</b>
                      {r.end_date !== r.start_date && <span> – {date(r.end_date, { day: "numeric", month: "short" })}</span>}
                    </span>
                    <span className="lc-up-type">{r.leave_label}</span>
                    <Status tone={STATUS_TONE[r.status]}>{STATUS_LABEL[r.status]}</Status>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <Card title="All leave" flush>
        <ErrorNote error={mine.error} onRetry={mine.reload} />
        <RequestList items={items} onWithdraw={withdraw} empty="You haven't asked for any leave yet." />
      </Card>
    </div>
  );
}
