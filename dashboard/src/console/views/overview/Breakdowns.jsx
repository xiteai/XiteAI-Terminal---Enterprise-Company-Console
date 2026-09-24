import { num, pct } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import BarList from "../../../charts/BarList.jsx";
import ChartCard from "../../../charts/ChartCard.jsx";
import Heatmap from "../../../charts/Heatmap.jsx";

const rows = (items) => items.map((i) => [i.label, num(i.value)]);
const pretty = (tool) => tool.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

// How the product is used, cut a few ways. Each chart is one series;
// version adoption picks out the latest version in ink.
export default function Breakdowns({ data }) {
  const { product } = useProduct();
  const w = words(product);
  const heatRows = data.heatmap.rows.flatMap((r, ri) => data.heatmap.values[ri].map((v, h) => [`${r} ${String(h).padStart(2, "0")}:00`, num(v)]));
  return (
    <>
      <div className="grid-2">
        <ChartCard title="Versions" subtitle={`Active ${w.many}, latest in black`} table={rows(data.versions)} columns={["Version", w.unit]}>
          <BarList items={data.versions} emphasis={data.latest_version} />
        </ChartCard>
        <ChartCard title="When it's used" subtitle={`Check-ins by weekday and hour · ${data.tz_label}`} table={heatRows} columns={["Hour", "Check-ins"]}>
          <Heatmap rows={data.heatmap.rows} values={data.heatmap.values} tzLabel={data.tz_label} />
        </ChartCard>
      </div>
      {data.age_bands && (
        <div className="grid-2">
          <ChartCard title="Age" subtitle={`${pct(data.profile_optin)} of active ${w.many} share it`}
            table={rows(data.age_bands)} columns={["Age band", "People"]}>
            <BarList items={data.age_bands} />
          </ChartCard>
          {data.regions && (
            <ChartCard title="Regions" subtitle={`Active ${w.many}`} table={rows(data.regions)} columns={["Region", w.unit]}>
              <BarList items={data.regions} />
            </ChartCard>
          )}
        </div>
      )}
      <div className="grid-2">
        <ChartCard title="Features" subtitle={`Uses, from the ${pct(data.usage_optin)} that share usage`}
          table={rows(data.tools)} columns={["Feature", "Uses"]}>
          <BarList items={data.tools.map((t) => ({ ...t, label: pretty(t.label) }))} empty="No usage shared yet." />
        </ChartCard>
        <ChartCard title={w.osMany} subtitle={`Active ${w.many}`} table={rows(data.os)} columns={[w.os, w.unit]}>
          <BarList items={data.os} />
        </ChartCard>
      </div>
    </>
  );
}
