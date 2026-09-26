import { Link } from "react-router-dom";
import { ageFrom, ago, date } from "../../../lib/format.js";
import { useSession } from "../../../lib/session.jsx";
import Card from "../../../components/Card.jsx";
import DetailList from "../../../components/DetailList.jsx";

const day = (iso) => (iso ? date(`${iso}T00:00:00`) : undefined);
const filled = (it) => it && it.value !== undefined && it.value !== null && it.value !== "" && it.value !== false;

// A titled section of label/value rows. It isn't drawn at all when there's
// nothing in it, so a partial profile never shows empty headings.
function Section({ title, items, columns = 2, extra }) {
  if (!items.some(filled) && !extra) return null;
  return (
    <Card title={title}>
      <DetailList columns={columns} items={items} />
      {extra}
    </Card>
  );
}

// Everything asked at sign-up, laid out the way HR reads it. Sections the
// viewer can't see simply don't arrive from the server.
export default function ProfileSections({ person: p }) {
  const { me } = useSession();
  const pr = p.profile || {};
  const age = ageFrom(pr.dob);
  const levelLabel = (key) => me?.levels?.find((l) => l.key === key)?.label || key;
  return (
    <>
      <Section title="Work" items={[
        { label: "Employee ID", value: p.employee_id },
        { label: "Work email", value: p.email },
        { label: "Level", value: p.level_label },
        { label: "Title", value: p.title },
        { label: "Team", value: p.department },
        { label: "Employment", value: p.employment_type },
        { label: "Start date", value: day(p.start_date) },
        { label: "Reports to", value: p.manager && <Link className="text-link" to={`/console/people/${p.manager.id}`}>{p.manager.display_name}</Link> },
      ]} extra={p.reports?.length > 0 && (
        <div className="pd-reports">
          <span>Their team</span>
          {p.reports.map((r) => <Link key={r.id} to={`/console/people/${r.id}`} className="pd-chip">{r.display_name}</Link>)}
        </div>
      )} />

      {p.full ? (
        <>
          <Section title="Personal" items={[
            { label: "Goes by", value: p.preferred_name !== p.display_name.split(" ")[0] ? p.preferred_name : undefined },
            { label: "Date of birth", value: pr.dob && `${day(pr.dob)} · ${age} years` },
            { label: "Gender", value: pr.gender },
            { label: "Phone", value: pr.phone },
            { label: "Personal email", value: pr.personal_email },
            { label: "City", value: pr.city },
            { label: "Address", value: pr.address },
          ]} />
          {pr.emergency && (
            <Section title="Emergency contact" columns={3} items={[
              { label: "Name", value: pr.emergency.name },
              { label: "Relationship", value: pr.emergency.relation },
              { label: "Phone", value: pr.emergency.phone },
            ]} />
          )}
          <Section title="Background" items={[
            { label: "Qualification", value: pr.education?.qualification },
            { label: "College or university", value: pr.education?.institution },
            { label: "Graduated", value: pr.education?.graduation_year },
            { label: "Experience", value: pr.experience?.years && `${pr.experience.years} years` },
            { label: "Most recent company", value: pr.experience?.previous_company },
            { label: "LinkedIn", value: pr.links?.linkedin && <a className="text-link" href={pr.links.linkedin} target="_blank" rel="noreferrer">{pr.links.linkedin}</a> },
            { label: "Portfolio", value: pr.links?.portfolio && <a className="text-link" href={pr.links.portfolio} target="_blank" rel="noreferrer">{pr.links.portfolio}</a> },
          ]} extra={(pr.skills?.length > 0 || pr.about) && (
            <>
              {pr.skills?.length > 0 && <p className="pd-skills"><b>Skills</b>{pr.skills.join(", ")}</p>}
              {pr.about && <blockquote className="pd-about">{pr.about}</blockquote>}
            </>
          )} />
          <Section title="Payroll" items={[
            { label: "PF number", value: p.pf_number },
            { label: "UAN", value: p.uan_number },
            { label: "Last promotion", value: p.last_promotion_at && day(p.last_promotion_at.slice(0, 10)) },
          ]} extra={p.promotions?.length > 0 && (
            <ul className="pd-promotions">
              {[...p.promotions].reverse().map((pr, i) => (
                <li key={i}>
                  <span className="pd-promo-at">{day(pr.at.slice(0, 10))}</span>
                  <span className="pd-promo-what">
                    {pr.from_title !== pr.to_title ? `${pr.from_title} → ${pr.to_title}` : pr.to_title}
                    {pr.from_level !== pr.to_level && <b> · {levelLabel(pr.to_level)}</b>}
                  </span>
                  <span className="pd-promo-by">by {pr.by_name}</span>
                </li>
              ))}
            </ul>
          )} />

          <Section title="Record" items={[
            { label: "Asked to join as", value: p.requested_label },
            { label: "Asked on", value: date(p.created_at) },
            { label: p.status === "declined" ? "Declined by" : p.status === "deactivated" ? "Deactivated by" : "Approved by", value: p.decided_by },
            { label: "Decided on", value: p.decided_at && date(p.decided_at) },
            { label: "Note", value: p.decision_note },
            { label: "Last sign-in", value: p.last_login_at ? ago(p.last_login_at) : p.is_demo ? "Demo person" : "Never" },
            { label: "Account", value: p.source === "env" ? "Managed in .env" : "Joined through sign-up" },
          ]} />
        </>
      ) : (
        <p className="t-note">Your level shows work details only. Full profiles are for the Founder and the people they allow.</p>
      )}
    </>
  );
}
