import { useEffect, useMemo } from "react";
import { Link, Navigate, Route, Routes, useParams } from "react-router-dom";
import { ProductProvider, rememberProduct } from "../../lib/product.jsx";
import { useSession } from "../../lib/session.jsx";
import Empty from "../../components/Empty.jsx";
import Installs from "../views/installs/Installs.jsx";
import Overview from "../views/overview/Overview.jsx";
import Releases from "../views/releases/Releases.jsx";
import Support from "../views/support/Support.jsx";
import Team from "../views/team/Team.jsx";
import Guard from "./Guard.jsx";
import { productNav } from "./nav.js";

// Everything inside one product. The product comes from the address, so a
// link to /console/p/xiteai-chat/support opens that product's support.
export default function ProductArea() {
  const { slug } = useParams();
  const { me, can } = useSession();
  const product = me.products.find((p) => p.slug === slug);
  useEffect(() => { if (product) rememberProduct(slug); }, [slug, product]);
  const ctx = useMemo(() => product && ({ product, slug, base: `/console/p/${slug}` }), [product, slug]);

  if (!product) {
    return (
      <div className="card">
        <Empty icon="box" title="This product isn't available."
          action={<Link className="text-link" to="/console">Back to all products</Link>}>
          It may be a demo product while demo data is hidden, or it was renamed.
        </Empty>
      </div>
    );
  }
  const first = productNav(product).find((n) => n.to && can(n.perm));
  const back = `/console/p/${slug}`;
  return (
    <ProductProvider value={ctx}>
      <Routes>
        <Route index element={can("overview") ? <Overview /> : first ? <Navigate to={first.to} replace /> : <Navigate to="/console" replace />} />
        <Route path="installs/:id?" element={<Guard perm="installs" fallback={back}><Installs /></Guard>} />
        <Route path="releases" element={<Guard perm="releases" fallback={back}><Releases /></Guard>} />
        <Route path="support/:id?" element={<Guard perm="support" fallback={back}><Support /></Guard>} />
        <Route path="team" element={<Guard perm="people.directory" fallback={back}><Team /></Guard>} />
        <Route path="*" element={<Navigate to={back} replace />} />
      </Routes>
    </ProductProvider>
  );
}
