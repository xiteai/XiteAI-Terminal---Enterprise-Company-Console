import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { num } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import { useSession } from "../../../lib/session.jsx";
import { useData, useDebounced } from "../../../lib/useData.js";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import InstallDrawer from "./InstallDrawer.jsx";
import InstallTable from "./InstallTable.jsx";
import Pager from "./Pager.jsx";
import "./Installs.css";

const STATES = [
  { value: "", label: "All" },
  { value: "active", label: "Active" },
  { value: "idle", label: "Idle" },
  { value: "dormant", label: "Dormant" },
  { value: "update_failed", label: "Update failed" },
  { value: "crashing", label: "Crashing" },
];

// Every copy of the product that has checked in, filterable and sortable.
export default function Installs() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { me } = useSession();
  const { product, slug, base } = useProduct();
  const w = words(product);
  const [q, setQ] = useState("");
  const [state, setState] = useState("");
  const [version, setVersion] = useState("");
  const [sort, setSort] = useState({ key: "last_seen", dir: "desc" });
  const [page, setPage] = useState(1);
  const query = useDebounced(q, 250);
  const { data, error, refreshing, reload } = useData(
    () => api.get(`/api/installs${qs({ product: slug, q: query, state, version, sort: sort.key, dir: sort.dir, page, page_size: 25 })}`),
    [slug, query, state, version, sort.key, sort.dir, page],
  );
  const onSort = (key) => {
    setPage(1);
    setSort((s) => ({ key, dir: s.key === key && s.dir === "desc" ? "asc" : "desc" }));
  };
  const states = product.kind === "web" ? STATES.filter((s) => s.value !== "update_failed") : STATES;

  return (
    <div>
      <PageHeader title={w.unit} subtitle={data ? data.customer_visibility : me.customer_visibility}
        meta={data && <><span><b>{num(data.total)}</b> matching</span><span>Latest version <b>{product.latest_version || "–"}</b></span></>} />
      <div className="toolbar">
        <Field icon="search" placeholder={`Search code, version, ${product.kind === "web" ? "browser" : "device"}…`} value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Seg size="sm" value={state} onChange={(v) => { setState(v); setPage(1); }} options={states} label="State" />
        <Select size="sm" value={version} onChange={(v) => { setVersion(v); setPage(1); }} placeholder="All versions"
          options={(data?.versions || []).map((v) => ({ value: v, label: v }))} />
      </div>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <div className={refreshing ? "is-refreshing" : ""}>
          <Card flush>
            <InstallTable items={data.items} sortable={data.sortable} sort={sort} onSort={onSort}
              latest={product.latest_version} onOpen={(install) => navigate(`${base}/installs/${install.id}`)} />
          </Card>
          <Pager page={data.page} pages={data.pages} total={data.total} onPage={setPage} />
        </div>
      )}
      <InstallDrawer id={id} onClose={() => navigate(`${base}/installs`)} onErased={() => { navigate(`${base}/installs`); reload(); }} />
    </div>
  );
}
