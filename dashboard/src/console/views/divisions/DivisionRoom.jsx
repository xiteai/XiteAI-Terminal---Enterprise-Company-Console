import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Empty from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import "./Divisions.css";

const TABS = [
  { key: "chat", label: "Chat", body: "A running channel for the team — coming next." },
  { key: "files", label: "Uploads", body: "Designs, docs and whatever else the team shares, in one place." },
  { key: "checkpoints", label: "Checkpoints", body: "What's due, what shipped, and who owns what." },
];

// A division's own room: its people down the side, and chat, uploads and
// checkpoints for that team once they're built — the door is open now.
export default function DivisionRoom() {
  const { name } = useParams();
  const nav = useNavigate();
  const label = decodeURIComponent(name);
  const people = useData(() => api.get("/api/people"), []);
  const [tab, setTab] = useState("chat");
  const members = useMemo(() => (people.data?.items || []).filter((p) => p.department === label), [people.data, label]);
  const active = TABS.find((t) => t.key === tab);

  return (
    <div className="stack">
      <PageHeader title={label} subtitle={`${members.length} ${members.length === 1 ? "person" : "people"} · this division's space.`}>
        <Button variant="quiet" icon="arrowLeft" onClick={() => nav("/console/divisions")}>All divisions</Button>
      </PageHeader>

      <div className="dr-layout">
        <Card>
          <div className="dr-tabs">
            {TABS.map((t) => (
              <button key={t.key} type="button" className={`dr-tab${t.key === tab ? " on" : ""}`} onClick={() => setTab(t.key)}>
                {t.label}
              </button>
            ))}
          </div>
          <Empty title="This room is being built.">{active.body}</Empty>
        </Card>

        <Card title="People">
          {members.length === 0 ? <Empty title="Nobody yet." /> : (
            <ul className="dr-members">
              {members.map((m) => (
                <li key={m.id}>
                  <Link to={`/console/people/${m.id}`} className="dr-member">
                    <Avatar src={m.avatar_url} initials={m.initials} level={m.level} size={30} />
                    <span className="dr-member-text">
                      <b>{m.display_name}</b>
                      <span>{m.title || m.level_label}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
