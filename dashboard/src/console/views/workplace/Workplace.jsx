import { Navigate, Route, Routes } from "react-router-dom";
import Guard from "../../shell/Guard.jsx";
import Approvals from "./Approvals.jsx";
import Assets from "./Assets.jsx";
import Expenses from "./Expenses.jsx";
import Handbook from "./Handbook.jsx";
import Helpdesk from "./Helpdesk.jsx";
import Leave from "./Leave.jsx";
import Pay from "./Pay.jsx";
import Ticket from "./Ticket.jsx";
import "./Workplace.css";

const DECIDE = ["leave.approve", "expenses.approve", "assets.approve"];

// Everything the team files against the company. Holding `workplace` is what
// gets you in here; the powers inside are checked page by page, and again on
// the server, which is the one that counts.
export default function Workplace() {
  return (
    <Routes>
      <Route index element={<Navigate to="leave" replace />} />
      <Route path="leave" element={<Leave />} />
      <Route path="expenses" element={<Expenses />} />
      <Route path="assets" element={<Assets />} />
      <Route path="helpdesk" element={<Helpdesk />} />
      <Route path="helpdesk/:id" element={<Ticket />} />
      <Route path="approvals" element={<Guard anyPerm={DECIDE}><Approvals /></Guard>} />
      <Route path="pay" element={<Pay />} />
      <Route path="handbook" element={<Handbook />} />
      <Route path="*" element={<Navigate to="/console/workplace/leave" replace />} />
    </Routes>
  );
}
