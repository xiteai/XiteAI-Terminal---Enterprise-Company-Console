import { createContext, useContext } from "react";

// The product a page is about. Everything under /console/p/:slug reads it
// from here; the server gets it as ?product=<slug>.
const ProductContext = createContext(null);
export const ProductProvider = ProductContext.Provider;
export const useProduct = () => useContext(ProductContext);

const KEY = "tc-product";
export function rememberProduct(slug) {
  try { localStorage.setItem(KEY, slug); } catch { /* a convenience only */ }
}
export function pickProduct(products, slug) {
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch { /* ignore */ }
  return products.find((p) => p.slug === slug) || products.find((p) => p.slug === saved) || products[0] || null;
}

// A desktop app has installs on Windows; a web app has users in browsers.
export function words(product) {
  const web = product?.kind === "web";
  return {
    unit: web ? "Users" : "Installs",
    one: web ? "user" : "install",
    many: web ? "users" : "installs",
    kind: web ? "Web app" : "Desktop app",
    os: web ? "Browser" : "Windows",
    osMany: web ? "Browsers" : "Windows versions",
  };
}

export const STATUS = {
  live: { label: "Live", tone: "good" },
  building: { label: "In development", tone: "info" },
  paused: { label: "Paused", tone: "neutral" },
};
