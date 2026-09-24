// How an install is doing, as a word and a tone. The tone only sets how the
// word is set (grey when fine, ink when it needs a look, red when broken);
// it never carries meaning alone.
export function presence(lastSeen) {
  const h = (Date.now() - new Date(lastSeen).getTime()) / 36e5;
  if (h < 24) return { label: "Active", tone: "good" };
  if (h < 24 * 7) return { label: "Idle", tone: "warn" };
  return { label: "Dormant", tone: "muted" };
}

export function health(install) {
  if (install.update_state === "failed") return { label: "Update failed", tone: "bad" };
  if (install.crash_count_7d > 0) return { label: `${install.crash_count_7d} crash${install.crash_count_7d > 1 ? "es" : ""}`, tone: "warn" };
  if (install.status === "relinked") return { label: "Re-linked", tone: "info" };
  return { label: "Healthy", tone: "good" };
}

// health/presence tone -> Status tone
export const statusTone = (tone) => (tone === "bad" ? "bad" : tone === "warn" || tone === "info" ? "warn" : "neutral");
