import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Birthdays from "./Birthdays.jsx";
import "./Home.css";
import Marquee from "./Marquee.jsx";
import PostModal from "./PostModal.jsx";
import Timeline from "./Timeline.jsx";

// Common to every team member: who's celebrating soon, what's coming up and
// what already happened, and the news worth telling everyone.
export default function Home() {
  const feed = useData(() => api.get("/api/feed"), []);
  const [posting, setPosting] = useState(false);
  const d = feed.data;

  const remove = async (p) => {
    feed.mutate((s) => (s ? {
      ...s,
      upcoming: s.upcoming.filter((x) => x.id !== p.id),
      results: s.results.filter((x) => x.id !== p.id),
      news: s.news.filter((x) => x.id !== p.id),
    } : s));
    try {
      await api.del(`/api/feed/${p.id}`);
    } finally {
      feed.reload();
    }
  };

  return (
    <div className="stack">
      <PageHeader title="Home" subtitle="What's happening across the company.">
        {d?.can_post && <Button variant="primary" icon="plus" onClick={() => setPosting(true)}>Post</Button>}
      </PageHeader>

      <ErrorNote error={feed.error} onRetry={feed.reload} />

      {d && (
        <>
          {d.upcoming.length > 0 && <Marquee items={d.upcoming} />}

          <section>
            <div className="section-head"><h2>Birthdays</h2></div>
            <Birthdays items={d.birthdays} />
          </section>

          <div className="grid-2 hm-grid">
            <Timeline title="Activity Hub" subtitle="Upcoming, and how it went"
              items={[...d.upcoming, ...d.results]} empty="Nothing on the calendar yet."
              onDelete={d.can_post ? remove : undefined} />
            <Timeline title="News" subtitle="Achievements, funding, announcements"
              items={d.news} empty="Nothing posted yet." onDelete={d.can_post ? remove : undefined} />
          </div>
        </>
      )}

      <PostModal open={posting} onClose={() => setPosting(false)} onDone={() => { setPosting(false); feed.reload(); }} />
    </div>
  );
}
