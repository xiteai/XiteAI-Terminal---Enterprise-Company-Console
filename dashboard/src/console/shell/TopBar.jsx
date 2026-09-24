import { Link, useMatch } from "react-router-dom";
import { useSession } from "../../lib/session.jsx";
import Icon from "../../components/Icon.jsx";
import Bell from "./Bell.jsx";
import { COMPANY_TITLES, productNav } from "./nav.js";

// Where you are, in plain words, then search and notifications.
function Crumbs() {
  const { me } = useSession();
  const inProduct = useMatch("/console/p/:slug/:section?/*");
  const company = useMatch("/console/:section/*");
  if (inProduct) {
    const product = me.products.find((p) => p.slug === inProduct.params.slug);
    const section = productNav(product).find((n) => n.to === (inProduct.params.section || ""));
    return (
      <ol className="tb-crumbs">
        <li><Link to="/console">Home</Link></li>
        {product && (
          <li><Link to={`/console/p/${product.slug}`} className="tb-crumb-product" aria-current={section?.to ? undefined : "page"}>{product.name}</Link></li>
        )}
        {section?.to && <li aria-current="page">{section.label}</li>}
      </ol>
    );
  }
  const title = COMPANY_TITLES[company?.params.section];
  return (
    <ol className="tb-crumbs">
      <li aria-current={title ? undefined : "page"}>{title ? <Link to="/console">Home</Link> : "Home"}</li>
      {title && <li aria-current="page">{title}</li>}
    </ol>
  );
}

export default function TopBar({ onSearch, onMenu }) {
  return (
    <header className="tb">
      <button className="tb-menu" onClick={onMenu} aria-label="Open menu"><Icon name="menu" size={19} /></button>
      <Crumbs />
      <div className="tb-right">
        <button className="tb-search" onClick={onSearch}>
          <Icon name="search" size={15} />
          <span>Search</span>
          <kbd>Ctrl K</kbd>
        </button>
        <Bell />
      </div>
    </header>
  );
}
