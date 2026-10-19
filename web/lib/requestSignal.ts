export function requestSignal(timeoutMs: number, callerSignal?: AbortSignal | null): AbortSignal {
  const timeout = AbortSignal.timeout(timeoutMs);
  return callerSignal ? AbortSignal.any([callerSignal, timeout]) : timeout;
}
