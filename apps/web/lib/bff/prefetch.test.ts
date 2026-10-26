import assert from "node:assert/strict";
import { test } from "node:test";

import { isPrefetchRequest } from "./prefetch";

test("detects Next.js router prefetch and RSC requests", () => {
  assert.equal(isPrefetchRequest(new Headers({ "Next-Router-Prefetch": "1" })), true);
  assert.equal(isPrefetchRequest(new Headers({ RSC: "1" })), true);
  assert.equal(isPrefetchRequest(new Headers({ Purpose: "prefetch" })), true);
  assert.equal(isPrefetchRequest(new Headers({ "Sec-Purpose": "prefetch;anonymous-client-ip" })), true);
});

test("does not flag a normal navigation", () => {
  assert.equal(isPrefetchRequest(new Headers({ Accept: "text/html" })), false);
});
