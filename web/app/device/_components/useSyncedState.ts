import { useCallback, useRef, useState, type RefObject } from "react";

export function useSyncedState<T>(initial: T): [T, (next: T) => void, RefObject<T>] {
  const [value, setValue] = useState(initial);
  const ref = useRef(initial);
  const set = useCallback((next: T) => {
    ref.current = next;
    setValue(next);
  }, []);
  return [value, set, ref];
}
