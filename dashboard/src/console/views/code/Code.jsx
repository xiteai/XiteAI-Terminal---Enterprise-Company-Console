import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import { useSession } from "../../../lib/session.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import AccessPage from "./AccessPage.jsx";
import ChangeDetail from "./ChangeDetail.jsx";
import Changes from "./Changes.jsx";
import CommitView from "./CommitView.jsx";
import Files from "./Files.jsx";
import Gate from "./Gate.jsx";
import GiveAccess from "./GiveAccess.jsx";
import History from "./History.jsx";
import CloneProgress from "./CloneProgress.jsx";
import Repos from "./Repos.jsx";
import Search from "./Search.jsx";
import "./Code.css";

// The company's code behind scoped access. GitHub stays the master copy; this
// is the gate in front of it: files, change requests, history, who was given
// what, and (for the founder) the repositories and their security.
const RepoContext = createContext(null);
export const useRepo = () => useContext(RepoContext);

export const MANAGE_PERMS = ["code.access_view", "code.grant", "code.grant_all", "code.owners", "code.revoke", "code.connect"];
// Anything that involves reading code. HR holds none of these: access list only.
const CODE_WORK = ["code.map", "code.request", "code.read_all", "code.merge_all", "code.grant", "code.grant_all", "code.owners", "code.connect"];
const REMEMBER = "tc-code-repo";
const SECTIONS = ["changes", "history", "access", "repos"];

function remembered() {
  try { return Number(localStorage.getItem(REMEMBER)) || null; } catch { return null; }
}

export default function Code() {
  const { can } = useSession();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [rid, setRid] = useState(remembered);
  const [cloning, setCloning] = useState(false);
  const [give, setGive] = useState(null);         // items to prefill "Give access" with, from anywhere in here
  const { data, error, reload } = useData(() => api.get("/api/code/repos"), [], { poll: cloning ? 2000 : undefined });

  useEffect(() => { setCloning(Boolean(data?.items.some((r) => r.status === "cloning"))); }, [data]);

  const ready = useMemo(() => (data?.items || []).filter((r) => r.status === "ready"), [data]);
  const repo = ready.find((r) => r.id === rid) || ready[0] || null;
  const choose = (id) => {
    setRid(id);
    try { localStorage.setItem(REMEMBER, String(id)); } catch { /* per-viewer convenience only */ }
  };

  const first = pathname.replace(/^\/console\/code\/?/, "").split("/")[0];
  const section = SECTIONS.includes(first) ? first : "files";
  const manage = MANAGE_PERMS.some(can);
  const works = CODE_WORK.some(can);
  const granter = can("code.grant") || can("code.grant_all");
  const repoAdmin = data && (data.can_connect || data.can_sync);
  const tabs = [
    ...(works ? [{ value: "files", label: "Files" }, { value: "changes", label: "Changes" }, { value: "history", label: "History" }] : []),
    ...(manage ? [{ value: "access", label: "Access" }] : []),
    ...(repoAdmin ? [{ value: "repos", label: "Repositories" }] : []),
  ];
  const go = (v) => navigate(v === "files" ? "/console/code" : `/console/code/${v}`);
  const ctx = useMemo(() => repo && {
    repo, rid: repo.id, reloadRepos: reload, choose, granter,
    giveAccess: granter ? (items) => setGive(items) : null,
  }, [repo, reload, granter]); // eslint-disable-line react-hooks/exhaustive-deps

  const gated = error?.status === 403 && ["authenticator", "paused"].includes(error.field);
  const held = (data?.items || []).find((r) => r.held_remote);
  return (
    <div>
      <PageHeader title="Codebase"
        subtitle="The company's code. Everyone sees only what they were given, and every change is reviewed before it reaches GitHub."
        meta={repo && <><span><b>{repo.name}</b> on {repo.branch}</span><span className="mono">{repo.head_sha.slice(0, 8)}</span></>}>
        {ready.length > 1 && (
          <Select size="sm" value={repo?.id} onChange={(v) => choose(Number(v))}
            options={ready.map((r) => ({ value: r.id, label: r.name }))} />
        )}
      </PageHeader>
      {gated && <Gate kind={error.field} />}
      {!gated && <ErrorNote error={error} onRetry={reload} />}
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <>
          {held && (
            <div className="callout callout-bad code-held">
              <span><b>GitHub's history for {held.name} was rewritten.</b> Someone force-pushed. Nothing is lost: the Terminal kept the
                real history and stopped following GitHub. {data.can_connect ? "Decide what happens next in Repositories." : "The founder decides what happens next."}</span>
            </div>
          )}
          {repo && works && (
            <RepoContext.Provider value={ctx}>
              <Search />
            </RepoContext.Provider>
          )}
          <Seg className="code-tabs" value={section} onChange={go} options={tabs} label="Codebase sections" />
          {!repo && section !== "repos" ? (
            <NoRepo data={data} onSetUp={() => go("repos")} />
          ) : (
            <RepoContext.Provider value={ctx}>
              <Routes>
                <Route index element={works ? <Files /> : <Navigate to="/console/code/access" replace />} />
                <Route path="changes" element={works ? <Changes /> : <Navigate to="/console/code/access" replace />} />
                <Route path="changes/:cid" element={works ? <ChangeDetail /> : <Navigate to="/console/code/access" replace />} />
                <Route path="history" element={works ? <History /> : <Navigate to="/console/code/access" replace />} />
                <Route path="history/compare/:base" element={works ? <CommitView compare /> : <Navigate to="/console/code/access" replace />} />
                <Route path="history/:sha" element={works ? <CommitView /> : <Navigate to="/console/code/access" replace />} />
                <Route path="access" element={manage ? <AccessPage /> : <Navigate to="/console/code" replace />} />
                <Route path="repos" element={repoAdmin ? <Repos data={data} reload={reload} /> : <Navigate to="/console/code" replace />} />
                <Route path="*" element={<Navigate to="/console/code" replace />} />
              </Routes>
              {repo && <GiveAccess open={Boolean(give)} initialItems={give || []} onClose={() => setGive(null)} />}
            </RepoContext.Provider>
          )}
        </>
      )}
    </div>
  );
}

function NoRepo({ data, onSetUp }) {
  const setting = data.items.find((r) => r.status === "cloning");
  const failed = data.items.find((r) => r.status === "failed");
  if (setting) return (
    <div className="empty">
      <p className="empty-title">{`Copying ${setting.name} from GitHub…`}</p>
      <div className="empty-action"><CloneProgress progress={setting.progress} /></div>
    </div>
  );
  return (
    <Empty title="No codebase is connected yet."
      action={data.can_connect && <button className="text-link" onClick={onSetUp}>Connect a GitHub repository</button>}>
      {failed ? `The last try failed: ${failed.status_detail}` : data.can_connect ? "Connect the company's GitHub repository to start." : "The founder connects it."}
    </Empty>
  );
}
