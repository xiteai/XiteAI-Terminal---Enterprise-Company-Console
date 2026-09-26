import { motion } from "../../../lib/motion.js";
import { useSession } from "../../../lib/session.jsx";
import { allowed } from "../../shell/nav.js";
import QuickLinkCard from "./QuickLinkCard.jsx";
import "./QuickLinks.css";

// Where the team actually goes. Each tile is a real place, and shows only if
// the viewer's level may go there — Approvals is nothing but a wall to
// someone with no one reporting to them.
const LINKS = [
  { label: "Leave", sub: "Book time off", art: "leave", to: "/console/workplace/leave", perm: "workplace" },
  { label: "IT Helpdesk", sub: "Raise a ticket", art: "helpdesk", to: "/console/workplace/helpdesk", perm: "workplace" },
  { label: "Expenses", sub: "Claim it back", art: "expense", to: "/console/workplace/expenses", perm: "workplace" },
  { label: "Asset Request", sub: "Ask for kit", art: "asset", to: "/console/workplace/assets", perm: "workplace" },
  { label: "Approvals", sub: "Waiting on you", art: "performance", to: "/console/workplace/approvals",
    anyPerm: ["leave.approve", "expenses.approve", "assets.approve"] },
  { label: "Payslips", sub: "Month by month", art: "pay", to: "/console/workplace/pay", perm: "workplace" },
  { label: "Team Directory", sub: "Who does what", art: "hr", to: "/console/people", perm: "people.directory" },
  { label: "Handbook", sub: "How we work", art: "handbook", to: "/console/workplace/handbook", perm: "workplace" },
];

const grid = { hidden: {}, show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } } };

export default function QuickLinks() {
  const { can } = useSession();
  const shown = LINKS.filter((l) => allowed(l, can));

  return (
    <motion.div className="ql-grid" variants={grid} initial="hidden" animate="show">
      {shown.map((l) => <QuickLinkCard key={l.label} link={l} />)}
    </motion.div>
  );
}
