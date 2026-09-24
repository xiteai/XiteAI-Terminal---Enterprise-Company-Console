import { useEffect, useState } from "react";

// Answers survive a refresh or an accidental close. The password never does.
const KEY = "tc-join-draft";

export function useDraft() {
  const [answers, setAnswers] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
      return saved && typeof saved === "object" ? saved : {};
    } catch {
      return {};
    }
  });
  useEffect(() => {
    try {
      const { password, agree_accurate, agree_storage, ...rest } = answers;
      localStorage.setItem(KEY, JSON.stringify(rest));
    } catch { /* a convenience only */ }
  }, [answers]);
  const clear = () => { try { localStorage.removeItem(KEY); } catch { /* ignore */ } };
  return [answers, setAnswers, clear];
}
