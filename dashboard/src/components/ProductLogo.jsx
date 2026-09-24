import { cx } from "../lib/cx.js";
import "./ProductLogo.css";

// A product's icon on its tile. White artwork (the XOS1 mark) sits on ink,
// dark artwork on white; a product without a logo shows its initials.
export default function ProductLogo({ product, size = 32, className }) {
  const style = { width: size, height: size, borderRadius: Math.round(size * 0.26) };
  const initials = (product?.name || "?").replace(/[^A-Za-z0-9 ]/g, "").split(/\s+/).map((w) => w[0]).join("").slice(0, 2);
  return (
    <span className={cx("plogo", product?.logo_invert ? "plogo-dark" : "plogo-light", className)} style={style} aria-hidden>
      {product?.logo
        ? <img src={`/brand/${product.logo}`} alt="" style={{ width: size * 0.62, height: size * 0.62 }} />
        : <b style={{ fontSize: size * 0.36 }}>{initials.toUpperCase()}</b>}
    </span>
  );
}
