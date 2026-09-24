import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, setOnUnauthorized, setPreview as setApiPreview } from "./api.js";

// Who is signed in, what their level may do, and (for the founder) which
// level they're previewing. Loaded once; refreshed after anything that could
// change it.
const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreviewState] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.get("/api/auth/me");
      setMe(data);
      setError(null);
      return data;
    } catch (e) {
      setError(e);
      return null;
    }
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => { window.location.assign("/login"); });
    refresh();
    return () => setOnUnauthorized(null);
  }, [refresh]);

  const setPreview = useCallback(async (level) => {
    setApiPreview(level);
    setPreviewState(level);
    await refresh();
  }, [refresh]);

  const value = useMemo(() => {
    const perms = new Set(me?.perms || []);
    return {
      me,
      error,
      refresh,
      preview,
      setPreview,
      can: (perm) => perms.has(perm),
      isFounder: Boolean(me?.user?.is_founder),
    };
  }, [me, error, refresh, preview, setPreview]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession outside SessionProvider");
  return ctx;
}
