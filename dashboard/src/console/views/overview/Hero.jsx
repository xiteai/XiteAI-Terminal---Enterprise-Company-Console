import { num } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import ChartCard from "../../../charts/ChartCard.jsx";
import LineChart from "../../../charts/LineChart.jsx";

// Day by day: how many installs (or users) were in use. The series from the
// server always ends on today, which is still in progress; plotting it would
// draw a cliff every morning, so the line stops at yesterday and today's
// count so far is stated in words. The table keeps every day.
export default function Activity({ data, range }) {
  const { product } = useProduct();
  const w = words(product);
  const series = data.active_series;
  const done = series.length > 1 ? series.slice(0, -1) : series;
  const today = series.length > 1 ? series[series.length - 1] : null;
  const peak = done.reduce((a, p) => (p.value > a.value ? p : a), done[0] || { value: 0 });
  return (
    <ChartCard
      title={`Active ${w.many} per day`}
      subtitle={`Peak ${num(peak.value)} in the last ${range} days${today ? ` · ${num(today.value)} today so far` : ""} · ${data.tz_label}`}
      table={series.map((p) => [p.date, num(p.value)])}
      columns={["Day", `Active ${w.many}`]}
    >
      <LineChart points={done} label={`Active ${w.many}`} height={260} />
    </ChartCard>
  );
}
