const RETRYABLE_MESSAGE =
  /network|fetch|server disconnected|connection|temporarily unavailable|timeout/i;

export function isRetryableRequestError(error) {
  if (!error || error.name === "AbortError") return false;

  if (typeof error.status === "number") {
    return error.status === 408 || error.status === 425 || error.status === 429 || error.status >= 500;
  }

  return error instanceof TypeError || RETRYABLE_MESSAGE.test(error.message || "");
}

export function wait(delayMs) {
  return new Promise((resolve) => window.setTimeout(resolve, delayMs));
}

export async function retryAsync(
  task,
  {
    attempts = 5,
    baseDelayMs = 750,
    maxDelayMs = 5000,
    shouldRetry = isRetryableRequestError,
    waitFn = wait,
  } = {},
) {
  let lastError;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      lastError = error;
      if (attempt === attempts || !shouldRetry(error)) throw error;

      const delayMs = Math.min(baseDelayMs * 2 ** (attempt - 1), maxDelayMs);
      await waitFn(delayMs);
    }
  }

  throw lastError;
}
