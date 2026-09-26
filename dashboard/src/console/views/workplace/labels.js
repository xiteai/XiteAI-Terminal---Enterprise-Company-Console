// How the Workplace says things, in one place so leave, expenses, assets and
// the helpdesk all word them the same way.

// Money arrives as whole paise and is never divided before it has to be.
export const rupees = (paise) =>
  `₹${((paise || 0) / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const STATUS_TONE = { pending: "warn", approved: "good", declined: "bad", withdrawn: "neutral" };
export const STATUS_LABEL = { pending: "Pending", approved: "Approved", declined: "Declined", withdrawn: "Withdrawn" };

export const TICKET_STATUS = {
  open: { label: "Open", tone: "warn" },
  in_progress: { label: "In progress", tone: "warn" },
  resolved: { label: "Resolved", tone: "good" },
  closed: { label: "Closed", tone: "neutral" },
};
export const PRIORITY = { urgent: "Urgent", high: "High", normal: "Normal", low: "Low" };

export const KIND_NOUN = { leave: "leave", expense: "expense claim", asset: "asset request" };

const short = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

// What each kind puts in the middle column of a list, in a word or two. Leave
// only reads as a range when the days picked actually are one — otherwise
// it's a list, because that's what an alternate-day request really is.
export function detail(r) {
  if (r.kind === "leave") {
    const dates = r.dates || [];
    if (dates.length <= 1) return short(r.start_date);
    const spanDays = (new Date(`${r.end_date}T00:00:00`) - new Date(`${r.start_date}T00:00:00`)) / 86400000 + 1;
    if (spanDays === dates.length) return `${short(r.start_date)} → ${short(r.end_date)}`;
    return dates.length > 5 ? `${dates.length} days, ${short(r.start_date)} – ${short(r.end_date)}` : dates.map(short).join(", ");
  }
  if (r.kind === "expense") return `${r.category_label} · ${r.spent_on}`;
  const action = r.asset_action === "replacement" ? " · Replacement" : "";
  return `${r.category_label}${r.quantity > 1 ? ` × ${r.quantity}` : ""}${action}`;
}

export function amount(r) {
  if (r.kind === "leave") return `${r.days} day${r.days === 1 ? "" : "s"}`;
  if (r.kind === "expense") return rupees(r.amount_paise);
  return r.quantity > 1 ? `${r.quantity} items` : "1 item";
}
