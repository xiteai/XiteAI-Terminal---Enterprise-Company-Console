import { useEffect, useState } from "react";
import { api } from "../../../../lib/api.js";
import { useSession } from "../../../../lib/session.jsx";

// What the approve / change-role forms can offer: levels below the viewer's
// own, the teams and titles, and who someone at a given level may report to.
export function useTeamOptions(open) {
  const { me } = useSession();
  const [opts, setOpts] = useState(null);
  const [org, setOrg] = useState([]);
  useEffect(() => {
    if (!open) return;
    api.get("/api/join/options").then(setOpts).catch(() => {});
    api.get("/api/people/org").then((r) => setOrg(r.items)).catch(() => {});
  }, [open]);
  const rank = Object.fromEntries(me.levels.map((l) => [l.key, l.rank]));
  const myRank = rank[me.level];
  const levels = me.levels.filter((l) => l.rank < myRank);
  const bossesFor = (level) => org.filter((p) => rank[p.level] > rank[level]);
  return { opts, levels, bossesFor, me };
}
