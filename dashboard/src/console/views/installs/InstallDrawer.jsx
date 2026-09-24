import { useState } from "react";
import { api, qs } from "../../../lib/api.js";
import { ago, date, dateTime, num } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import { useData } from "../../../lib/useData.js";
import BarList from "../../../charts/BarList.jsx";
import { Status } from "../../../components/Badge.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import DetailList from "../../../components/DetailList.jsx";
import Drawer from "../../../components/Drawer.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import Spinner from "../../../components/Spinner.jsx";
import ActivityStrip from "./ActivityStrip.jsx";
import EraseInstall from "./EraseInstall.jsx";
import { health, presence, statusTone } from "./health.js";

// One install, in full (as far as the viewer's level allows).
export default function InstallDrawer({ id, onClose, onErased }) {
  const { product, slug } = useProduct();
  const w = words(product);
  const { data, error, reload } = useData(() => (id ? api.get(`/api/installs/${id}${qs({ product: slug })}`) : Promise.resolve(null)), [id, slug]);
  const [erase, setErase] = useState(false);
  const i = data?.install;
  const person = i?.person || {};
  const h = i && health(i);
  const p = i && presence(i.last_seen);
  return (
    <Drawer open={Boolean(id)} onClose={onClose} eyebrow={i ? `${product.name} ${w.one} · ${i.code}` : product.name}
      title={i ? (person.name || i.code) : "Loading…"} width={600}>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {i && (
        <>
          <p className="in-facts">
            <span>{p.label}</span>
            <Status tone={statusTone(h.tone)}>{h.label}</Status>
            <span>Version {i.app_version}</span>
            {i.is_demo && <span>Demo</span>}
          </p>

          <Card title="Last 30 days">
            <ActivityStrip days={data.daily} />
          </Card>

          <Card title="The person">
            {person.consented ? (
              <DetailList columns={2} items={[
                { label: "Name", value: person.name },
                { label: "Date of birth", value: person.dob && date(`${person.dob}T00:00:00`) },
                { label: "Age", value: person.age },
                { label: "Age band", value: person.age === undefined ? person.age_band : undefined },
                { label: "Region", value: i.region },
                { label: "Time zone", value: i.timezone },
              ]} />
            ) : (
              <p className="t-note">They chose not to share their name or age.</p>
            )}
            {person.consented && !("name" in person) && !("age" in person) && !("age_band" in person) && (
              <p className="t-note">Your level doesn't show personal details.</p>
            )}
          </Card>

          <Card title={product.kind === "web" ? "The browser" : "The machine"}>
            <DetailList columns={2} items={[
              { label: "Code", value: i.code, mono: true },
              { label: "Device", value: i.device_type },
              { label: w.os, value: i.os_version },
              { label: "Language", value: i.locale },
              { label: "First seen", value: date(i.first_seen) },
              { label: "Last seen", value: `${ago(i.last_seen)} · ${dateTime(i.last_seen)}` },
              { label: "Check-ins", value: num(i.checkin_count) },
              { label: "Shares usage", value: i.consent_usage ? "Yes" : "No" },
              { label: "Hardware ID (hashed)", value: i.hardware_hash && `${i.hardware_hash.slice(0, 24)}…`, mono: true },
              { label: "Key fingerprint", value: i.key_fingerprint, mono: true },
            ]} />
          </Card>

          {data.versions.length > 0 && (
            <Card title="Versions it has run">
              <ol className="d-timeline">
                {data.versions.map((v) => (
                  <li key={`${v.version}-${v.since}`}><span className="mono">{v.version}</span><span>since {date(v.since)}</span></li>
                ))}
              </ol>
            </Card>
          )}

          {data.tools.length > 0 && (
            <Card title="What it's used for">
              <BarList items={data.tools.map((t) => ({ ...t, label: t.label.replace(/_/g, " ") }))} />
            </Card>
          )}

          {data.key_history.length > 0 && (
            <Card title="Earlier keys">
              <div className="callout"><Icon name="alert" size={16} /><span>This machine checked in with a new key: a reinstall, or someone copying its identity.</span></div>
              <DetailList items={data.key_history.map((k) => ({ label: `Replaced ${date(k.replaced_at)}`, value: k.fingerprint, mono: true }))} />
            </Card>
          )}

          {data.can_erase && (
            <Card title="Erase">
              <div className="d-danger">
                <p className="t-note">Deletes every record we hold for this {w.one}: check-ins, name, age and keys. It can't be undone.</p>
                <Button variant="danger" onClick={() => setErase(true)}>Erase</Button>
              </div>
            </Card>
          )}
          <EraseInstall open={erase} install={i} onClose={() => setErase(false)} onDone={onErased} />
        </>
      )}
    </Drawer>
  );
}
