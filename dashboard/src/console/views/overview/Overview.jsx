import { useState } from "react";
import { api, qs } from "../../../lib/api.js";
import { STATUS, useProduct } from "../../../lib/product.jsx";
import { useSession } from "../../../lib/session.jsx";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import ProductLogo from "../../../components/ProductLogo.jsx";
import Seg from "../../../components/Seg.jsx";
import Spinner from "../../../components/Spinner.jsx";
import Activity from "./Hero.jsx";
import Breakdowns from "./Breakdowns.jsx";
import EditProductModal from "./EditProductModal.jsx";
import Figures from "./KpiGrid.jsx";
import RecentCheckins from "./RecentCheckins.jsx";
import "./Overview.css";

const RANGES = [{ value: 7, label: "7 days" }, { value: 30, label: "30 days" }, { value: 90, label: "90 days" }];

// One product at a glance: the headline numbers, activity day by day, and how
// it's used, cut a few ways.
export default function Overview() {
  const { product, slug } = useProduct();
  const { can } = useSession();
  const [range, setRange] = useState(30);
  const [editing, setEditing] = useState(false);
  const { data, error, refreshing, reload } = useData(() => api.get(`/api/overview${qs({ range, product: slug })}`), [range, slug]);
  const status = product.status && product.status !== "live" ? STATUS[product.status]?.label : null;
  const time = data ? new Date(data.generated_at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }) : "";

  return (
    <div>
      <PageHeader
        lead={<ProductLogo product={product} size={40} />}
        title={product.name}
        badge={product.is_demo && <span className="demo-tag">Demo</span>}
        subtitle={product.description}
        meta={<>
          {status && <span>{status}</span>}
          {product.latest_version && <span>Version <b>{product.latest_version}</b></span>}
          {data && <span>Updated {time} {data.tz_label}</span>}
          {product.website && <a className="text-link ov-site" href={product.website} target="_blank" rel="noreferrer">{product.website.replace(/^https?:\/\//, "")}</a>}
        </>}
      >
        <Seg value={range} onChange={setRange} options={RANGES} label="Period" />
        {can("products.manage") && <Button variant="ghost" onClick={() => setEditing(true)}>Edit</Button>}
      </PageHeader>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <div className={`stack ${refreshing ? "is-refreshing" : ""}`}>
          <Figures data={data} range={range} />
          <Activity data={data} range={range} />
          <Breakdowns data={data} />
          <RecentCheckins items={data.recent} />
        </div>
      )}
      <EditProductModal open={editing} onClose={() => setEditing(false)} />
    </div>
  );
}
