import { date } from "../../lib/format.js";
import { SECTIONS, STEP_OF_FIELD, STEPS } from "./steps.js";

// Every answer, grouped by part, on the review step. Each part has an Edit
// link that goes back to its first question.
function rows(a, meta) {
  const level = meta?.levels?.find((l) => l.key === a.level)?.label;
  return [
    [0, "Full name", "full_name", a.full_name],
    [0, "Goes by", "preferred_name", a.preferred_name],
    [0, "Work email", "local", a.local && `${a.local}@${meta?.domain || "xos1.com"}`],
    [0, "Password", "password", a.password && "Set"],
    [1, "Level", "level", level],
    [1, "Team", "department", a.department],
    [1, "Title", "title", a.title],
    [1, "Employment", "employment_type", a.employment_type],
    [1, "Starts", "start_date", a.start_date && date(`${a.start_date}T00:00:00`)],
    [2, "Date of birth", "dob", a.dob && date(`${a.dob}T00:00:00`)],
    [2, "Gender", "gender", a.gender],
    [2, "Phone", "phone", a.phone],
    [2, "Personal email", "personal_email", a.personal_email],
    [2, "City", "city", a.city],
    [2, "Address", "address", a.address],
    [3, "Name", "emergency_name", a.emergency_name],
    [3, "Relationship", "emergency_relation", a.emergency_relation],
    [3, "Phone", "emergency_phone", a.emergency_phone],
    [4, "Qualification", "qualification", a.qualification],
    [4, "Studied at", "institution", a.institution],
    [4, "Graduated", "graduation_year", a.graduation_year],
    [4, "Experience", "experience_years", a.experience_years && `${a.experience_years} years`],
    [4, "Previously at", "previous_company", a.previous_company],
    [4, "Skills", "skills", a.skills],
    [4, "LinkedIn", "linkedin", a.linkedin],
    [4, "Portfolio", "portfolio", a.portfolio],
    [4, "About", "about", a.about],
  ];
}

const firstStep = (s) => STEPS.findIndex((st) => st.section === s && st.kind !== "intro");

export default function Summary({ answers, meta, onJump }) {
  const list = rows(answers, meta);
  return (
    <div className="jsum">
      {SECTIONS.slice(0, 5).map((name, s) => {
        const items = list.filter((r) => r[0] === s);
        const filled = items.filter((r) => r[3]);
        return (
          <section className="jsum-group" key={name}>
            <header>
              <b>{name}</b>
              <button type="button" className="text-link" onClick={() => onJump(firstStep(s))}>Edit</button>
            </header>
            {filled.length === 0 ? <p className="jsum-none">Skipped</p> : (
              <dl>
                {filled.map(([, label, key, value]) => (
                  <div key={key} className="jsum-row">
                    <dt>{label}</dt>
                    <dd><button type="button" onClick={() => onJump(STEP_OF_FIELD[key])}>{value}</button></dd>
                  </div>
                ))}
              </dl>
            )}
          </section>
        );
      })}
    </div>
  );
}
