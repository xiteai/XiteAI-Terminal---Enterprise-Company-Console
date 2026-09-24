import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { useSession } from "../../lib/session.jsx";
import ErrorBoundary from "../../components/ErrorBoundary.jsx";
import Access from "../views/access/Access.jsx";
import Account from "../views/account/Account.jsx";
import Audit from "../views/audit/Audit.jsx";
import Code from "../views/code/Code.jsx";
import Home from "../views/home/Home.jsx";
import Keys from "../views/keys/Keys.jsx";
import People from "../views/people/People.jsx";
import CommandPalette from "./CommandPalette.jsx";
import Guard from "./Guard.jsx";
import ProductArea from "./ProductArea.jsx";
import Sidebar from "./Sidebar.jsx";
import { CODE_PERMS } from "./nav.js";
import TopBar from "./TopBar.jsx";
import "./Shell.css";

// Links from before products existed (/console/installs/12) land in XOS1.
function Legacy({ section }) {
  const rest = useParams()["*"];
  return <Navigate to={`/console/p/xos1/${section}${rest ? `/${rest}` : ""}`} replace />;
}

// The console: a sidebar to move around, a top bar that says where you are,
// and the page. Switching pages is a short fade, never a wait.
export default function Shell() {
  const location = useLocation();
  const { me, preview, setPreview } = useSession();
  const [palette, setPalette] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const parts = location.pathname.split("/");
  const pageKey = parts[2] === "p" ? parts.slice(0, 5).join("/") : parts.slice(0, 3).join("/");

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((p) => !p); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => { setNavOpen(false); window.scrollTo(0, 0); }, [pageKey]);

  return (
    <div className="app">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="app-main">
        <TopBar onSearch={() => setPalette(true)} onMenu={() => setNavOpen(true)} />
        {preview && (
          <div className="preview-bar" role="status">
            <span>Previewing as <b>{me.level_label}</b>. You see exactly what they see, and nothing can be changed.</span>
            <button onClick={() => setPreview(null)}>Stop preview</button>
          </div>
        )}
        <main className="app-content">
          <div key={`${pageKey}-${preview || "self"}-${me.show_demo}`} className="fade-in">
            <ErrorBoundary resetKey={pageKey}>
              <Routes>
                <Route index element={<Home />} />
                <Route path="p/:slug/*" element={<ProductArea />} />
                <Route path="people/*" element={<Guard perm="people.directory"><People /></Guard>} />
                <Route path="code/*" element={<Guard anyPerm={CODE_PERMS}><Code /></Guard>} />
                <Route path="keys" element={<Guard perm="keys.view"><Keys /></Guard>} />
                <Route path="access" element={<Guard perm="access.manage"><Access /></Guard>} />
                <Route path="audit" element={<Guard perm="audit.view"><Audit /></Guard>} />
                <Route path="account" element={<Account />} />
                <Route path="installs/*" element={<Legacy section="installs" />} />
                <Route path="releases" element={<Legacy section="releases" />} />
                <Route path="support/*" element={<Legacy section="support" />} />
                <Route path="*" element={<Navigate to="/console" replace />} />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  );
}
