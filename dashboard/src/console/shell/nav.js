import { words } from "../../lib/product.jsx";

// The console's places. A place shows only if the viewer's level holds its
// permission (the server refuses the data regardless).

// Inside a product: paths are relative to /console/p/<slug>.
export const productNav = (product) => [
  { to: "", end: true, label: "Overview", icon: "overview", perm: "overview" },
  { to: "installs", label: words(product).unit, icon: product?.kind === "web" ? "browser" : "installs", perm: "installs" },
  { to: "releases", label: "Releases", icon: "releases", perm: "releases" },
  { to: "support", label: "Support", icon: "support", perm: "support" },
  { to: "team", label: "Team", icon: "briefcase", perm: "people.directory" },
];

// Anyone holding one of these sees the Codebase (HR only for who-has-what).
export const CODE_PERMS = ["code.map", "code.request", "code.read_all", "code.access_view", "code.grant",
  "code.grant_all", "code.owners", "code.merge_all", "code.revoke", "code.connect"];

// A place shows when the viewer holds its `perm`, or any of its `anyPerm`.
export const allowed = (n, can) => (n.anyPerm ? n.anyPerm.some(can) : can(n.perm));

// Across the company.
export const COMPANY_NAV = [
  { to: "/console/people", label: "People", icon: "people", perm: "people.directory", badge: "pending_requests" },
  { to: "/console/code", label: "Codebase", icon: "code", anyPerm: CODE_PERMS },
  { to: "/console/keys", label: "AI keys", icon: "key", perm: "keys.view" },
  { to: "/console/access", label: "Access", icon: "access", perm: "access.manage" },
  { to: "/console/audit", label: "Audit log", icon: "audit", perm: "audit.view" },
];

export const COMPANY_TITLES = {
  people: "People",
  code: "Codebase",
  keys: "AI keys",
  access: "Access",
  audit: "Audit log",
  account: "Account",
};
