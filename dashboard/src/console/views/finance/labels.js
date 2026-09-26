export const rupees = (paise) =>
  `₹${((paise || 0) / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

export const rupeesCompact = (paise) => {
  const n = (paise || 0) / 100;
  const a = Math.abs(n);
  if (a >= 1e7) return `₹${(n / 1e7).toFixed(a >= 1e8 ? 0 : 1)}Cr`;
  if (a >= 1e5) return `₹${(n / 1e5).toFixed(a >= 1e6 ? 0 : 1)}L`;
  if (a >= 1e3) return `₹${(n / 1e3).toFixed(a >= 1e4 ? 0 : 1)}K`;
  return `₹${n.toFixed(0)}`;
};

export const monthLabel = (period) =>
  new Date(`${period}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
