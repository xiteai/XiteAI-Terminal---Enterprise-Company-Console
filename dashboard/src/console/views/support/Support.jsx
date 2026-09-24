import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { useProduct } from "../../../lib/product.jsx";
import { useData, useDebounced } from "../../../lib/useData.js";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import TicketList from "./TicketList.jsx";
import TicketPane from "./TicketPane.jsx";
import { KIND_LABEL } from "./labels.js";
import "./Support.css";

// An inbox: requests on the left, the open one on the right.
export default function Support() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { product, slug, base } = useProduct();
  const [status, setStatus] = useState("active");
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");
  const query = useDebounced(q, 250);
  const list = useData(() => api.get(`/api/tickets${qs({ product: slug, status, kind, q: query })}`), [slug, status, kind, query]);
  // Counts show once they're known (never a "0" that then jumps to 11).
  const counts = list.data?.counts;
  const n = (k) => (counts ? counts[k] || 0 : undefined);
  const tabs = [
    { value: "active", label: "Open", count: counts ? n("open") + n("in_progress") : undefined },
    { value: "resolved", label: "Resolved", count: n("resolved") },
    { value: "closed", label: "Closed", count: n("closed") },
    { value: "", label: "All" },
  ];

  return (
    <div>
      <PageHeader title="Support" subtitle={`Requests about ${product.name} from the customer page. Notes are internal.`} />
      <div className="sp">
        <aside className="sp-list">
          <div className="sp-list-head">
            <Seg size="sm" value={status} onChange={setStatus} options={tabs} label="Status" />
            <div className="sp-filter-row">
              <Field icon="search" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} className="sp-search" />
              <Select size="sm" value={kind} onChange={setKind} placeholder="All kinds"
                options={Object.entries(KIND_LABEL).map(([value, label]) => ({ value, label }))} />
            </div>
          </div>
          <ErrorNote error={list.error} onRetry={list.reload} />
          {list.data && <TicketList items={list.data.items} selected={Number(id)} onOpen={(t) => navigate(`${base}/support/${t.id}`)} />}
        </aside>
        <section className="sp-pane">
          {id ? <TicketPane id={id} onChanged={list.reload} /> : (
            <Empty title="No request selected">Choose one from the list to read it, assign it or add a note.</Empty>
          )}
        </section>
      </div>
    </div>
  );
}
