import { useCallback, useEffect, useRef, useState } from "react";

// Load something from the server. While it reloads, the previous data stays on
// screen (no skeleton flash, no layout jump); `refreshing` lets a view dim it.
export function useData(fetcher, deps = [], { poll } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true, refreshing: false });
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, error: null, refreshing: s.data !== null }));
    fetcherRef.current()
      .then((data) => alive && setState({ data, error: null, loading: false, refreshing: false }))
      .catch((error) => alive && setState((s) => ({ ...s, error, loading: false, refreshing: false })));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  useEffect(() => {
    if (!poll) return undefined;
    const id = setInterval(() => { if (!document.hidden) setTick((t) => t + 1); }, poll);
    return () => clearInterval(id);
  }, [poll]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  const mutate = useCallback((fn) => setState((s) => ({ ...s, data: fn(s.data) })), []);
  return { ...state, reload, mutate };
}

export function useDebounced(value, ms = 250) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}
