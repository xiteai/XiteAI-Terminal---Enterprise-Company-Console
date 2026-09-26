import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import CompanyCards from "./CompanyCards.jsx";
import NewProductModal from "./NewProductModal.jsx";
import ProductCard from "./ProductCard.jsx";
import "./Products.css";

// Every product with its headline numbers, then the company at a glance.
// Open a product to go inside it.
export default function Products() {
  const { can } = useSession();
  const [creating, setCreating] = useState(false);
  const products = useData(() => api.get("/api/products"), []);
  const company = useData(() => (can("people.directory") ? api.get("/api/company") : Promise.resolve(null)), []);

  return (
    <div className="stack">
      <PageHeader title="Products">
        {can("products.manage") && <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>New product</Button>}
      </PageHeader>

      <section>
        <div className="section-head"><h2>Products</h2></div>
        <ErrorNote error={products.error} onRetry={products.reload} />
        <div className="home-products">
          {(products.data?.items || []).map((p) => <ProductCard key={p.slug} product={p} />)}
        </div>
      </section>

      {company.data && <CompanyCards data={company.data} />}
      <NewProductModal open={creating} onClose={() => setCreating(false)} onDone={products.reload} />
    </div>
  );
}
