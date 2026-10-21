import test from "node:test";
import assert from "node:assert/strict";

import { isRetryableRequestError, retryAsync } from "../lib/retry.mjs";

test("retryAsync retries transient failures and returns the eventual result", async () => {
  let calls = 0;
  const delays = [];

  const result = await retryAsync(
    async () => {
      calls += 1;
      if (calls < 3) {
        const error = new Error("Server disconnected");
        error.status = 503;
        throw error;
      }
      return "restored";
    },
    { waitFn: async (delay) => delays.push(delay) },
  );

  assert.equal(result, "restored");
  assert.equal(calls, 3);
  assert.deepEqual(delays, [750, 1500]);
});

test("retryAsync does not retry a non-retryable client error", async () => {
  let calls = 0;
  const error = new Error("Forbidden");
  error.status = 403;

  await assert.rejects(
    retryAsync(
      async () => {
        calls += 1;
        throw error;
      },
      { waitFn: async () => {} },
    ),
    error,
  );

  assert.equal(calls, 1);
});

test("retryable request classification covers network and server failures", () => {
  const serverError = new Error("Unavailable");
  serverError.status = 503;
  const authError = new Error("Unauthorized");
  authError.status = 401;

  assert.equal(isRetryableRequestError(serverError), true);
  assert.equal(isRetryableRequestError(new TypeError("Failed to fetch")), true);
  assert.equal(isRetryableRequestError(authError), false);
});
