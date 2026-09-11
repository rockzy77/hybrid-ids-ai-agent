import { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { api } from "./api";

const FeedContext = createContext(null);

const MAX_ITEMS = 250;
const CLEAN_ITEM_LIFETIME_MS = 4200; // how long a 'clean' row stays before it's removed

export function FeedProvider({ children }) {
  const [items, setItems] = useState([]);
  const [isPolling, setIsPolling] = useState(true);
  const [intervalSeconds, setIntervalSeconds] = useState(4);
  const [connectionError, setConnectionError] = useState(null);
  const [queueExhausted, setQueueExhausted] = useState(false);
  const nextKeyRef = useRef(0);

  const pushCleanItem = useCallback((result) => {
    const key = `clean-${nextKeyRef.current++}`;
    setItems((prev) => [{ kind: "clean", key, ...result, receivedAt: Date.now() }, ...prev].slice(0, MAX_ITEMS));
    setTimeout(() => {
      setItems((prev) => prev.filter((i) => i.key !== key));
    }, CLEAN_ITEM_LIFETIME_MS);
  }, []);

  const pushAlertItem = useCallback((result) => {
    setItems((prev) => [
      { kind: "alert", key: `alert-${result.id}`, ...result, receivedAt: Date.now() },
      ...prev,
    ].slice(0, MAX_ITEMS));
  }, []);

  const pollNextTraffic = useCallback(async () => {
    try {
      const result = await api.getNextTraffic();
      setConnectionError(null);
      if (result === null) {
        setQueueExhausted(true);
        return;
      }
      setQueueExhausted(false);
      if (result.is_attack) {
        pushAlertItem(result);
      } else {
        pushCleanItem(result);
      }
    } catch (err) {
      setConnectionError(err.message);
    }
  }, [pushAlertItem, pushCleanItem]);

  const syncAlertStatuses = useCallback(async () => {
    try {
      const allAlerts = await api.getAlerts();
      setConnectionError(null);
      setItems((prev) =>
        prev.map((item) => {
          if (item.kind !== "alert") return item;
          const match = allAlerts.find((a) => a.id === item.id);
          if (!match) return item;
          return { ...item, ...match, kind: "alert" };
        })
      );
    } catch (err) {
      setConnectionError(err.message);
    }
  }, []);

  useEffect(() => {
    if (!isPolling) return undefined;
    const trafficTimer = setInterval(pollNextTraffic, intervalSeconds * 1000);
    const statusTimer = setInterval(syncAlertStatuses, 2500);
    return () => {
      clearInterval(trafficTimer);
      clearInterval(statusTimer);
    };
  }, [isPolling, intervalSeconds, pollNextTraffic, syncAlertStatuses]);

  const value = {
    items,
    isPolling,
    setIsPolling,
    intervalSeconds,
    setIntervalSeconds,
    connectionError,
    queueExhausted,
  };

  return <FeedContext.Provider value={value}>{children}</FeedContext.Provider>;
}

export function useFeed() {
  const ctx = useContext(FeedContext);
  if (!ctx) throw new Error("useFeed must be used within a FeedProvider");
  return ctx;
}
