import { Link } from "react-router-dom";
import Avatar from "../../../components/Avatar.jsx";
import Icon from "../../../components/Icon.jsx";
import { birthdayLine } from "./labels.js";

// Who's celebrating soon — a small, quiet marquee, not a card row. Today's
// person gets a warm chip; the rest just scroll past.
export default function Birthdays({ items }) {
  if (!items.length) {
    return <p className="hm-quiet"><Icon name="calendar" size={15} />No birthdays in the next two weeks.</p>;
  }
  const loop = items.length > 3 ? [...items, ...items] : items;
  return (
    <div className="hm-bday-marquee" role="list" aria-label="Upcoming birthdays">
      <div className={`hm-bday-track${items.length > 3 ? "" : " hm-bday-static"}`}>
        {loop.map((b, i) => (
          <Link key={`${b.id}-${i}`} role="listitem" to={`/console/people/${b.id}`}
            className={`hm-bday-chip${b.days_away === 0 ? " hm-bday-today" : ""}`}>
            <Avatar src={b.avatar_url} initials={b.name[0]} size={26} />
            <span>{b.name}</span>
            <i>{birthdayLine(b)}</i>
          </Link>
        ))}
      </div>
    </div>
  );
}
