import { NavLink, Route, Routes } from "react-router-dom";
import { useSession } from "../../../lib/session.jsx";
import { cx } from "../../../lib/cx.js";
import PageHeader from "../../../components/PageHeader.jsx";
import Directory from "./Directory.jsx";
import OrgChart from "./OrgChart.jsx";
import Requests from "./Requests.jsx";
import "./People.css";

// Everyone at XiteAI, how they fit together, and who's asking to join.
export default function People() {
  const { me, can } = useSession();
  const pending = me.counts?.pending_requests || 0;
  const tabs = [
    { to: "/console/people", end: true, label: "Directory" },
    { to: "/console/people/org", label: "Org chart" },
    ...(can("people.approve") ? [{ to: "/console/people/requests", label: "Join requests", count: pending }] : []),
  ];
  return (
    <div>
      <PageHeader title="People" subtitle={can("people.profiles")
        ? "Everyone at XiteAI. Open anyone to see their full profile."
        : "Names, roles and teams. Full profiles are for the people the Founder allows."} />
      <nav className="tabs" aria-label="People">
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => cx("tab", isActive && "on")}>
            {t.label}
            {t.count > 0 && <span className="tab-count tnum">{t.count}</span>}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route index element={<Directory />} />
        <Route path="org" element={<OrgChart />} />
        <Route path="requests/:rid?" element={<Requests />} />
        <Route path=":id" element={<Directory />} />
      </Routes>
    </div>
  );
}
