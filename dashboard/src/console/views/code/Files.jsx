import { useSearchParams } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useRepo } from "./Code.jsx";
import FileView from "./FileView.jsx";
import Tree from "./Tree.jsx";

// The map on the left, the open file on the right. The open file lives in the
// address (?path=), so a link to it can be shared with someone who has access.
export default function Files() {
  const { rid, repo } = useRepo();
  const [params, setParams] = useSearchParams();
  const path = params.get("path");
  const { data, error, reload } = useData(() => api.get(`/api/code/${rid}/tree`), [rid, repo.head_sha]);
  const pick = (f) => setParams(f ? { path: f.p } : {}, { replace: false });

  return (
    <div className="code-files">
      <aside className="code-side">
        <ErrorNote error={error} onRetry={reload} />
        {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
        {data && <Tree files={data.files} selected={path} onSelect={pick} />}
      </aside>
      <section className="code-main">
        {path ? (
          <FileView key={`${path}@${repo.head_sha}`} path={path} line={Number(params.get("line")) || null} canRequest={data?.can_request} />
        ) : (
          <Empty title="Pick a file.">
            Files you can open have a word next to them: <b>edit</b>, <b>read</b>, or <b>part</b> when you were given some of
            its lines. A lock means it isn't shared with you.
          </Empty>
        )}
      </section>
    </div>
  );
}
