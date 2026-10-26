/** True for Next.js router prefetch / RSC requests, which must not trigger side effects. */
export function isPrefetchRequest(headers: Headers): boolean {
  return (
    headers.has("next-router-prefetch") ||
    headers.has("rsc") ||
    headers.get("purpose") === "prefetch" ||
    headers.get("sec-purpose")?.startsWith("prefetch") === true
  );
}
