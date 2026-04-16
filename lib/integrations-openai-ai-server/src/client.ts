import OpenAI from "openai";

/**
 * Google Gemini via the OpenAI-compatible HTTP API (same request shape as chat completions).
 * @see https://ai.google.dev/gemini-api/docs/openai
 */
const DEFAULT_GEMINI_OPENAI_BASE =
  "https://generativelanguage.googleapis.com/v1beta/openai/";

const baseURL =
  process.env.GEMINI_BASE_URL?.trim() || DEFAULT_GEMINI_OPENAI_BASE;

const apiKey = process.env.GEMINI_API_KEY?.trim();
if (!apiKey) {
  throw new Error(
    "GEMINI_API_KEY must be set. Create a key in Google AI Studio: https://aistudio.google.com/apikey",
  );
}

/**
 * The OpenAI SDK only reads `responseJson.error` when building APIError messages. Gemini may
 * return valid JSON error payloads without that exact shape, which surfaces as
 * "400 status code (no body)" even when a body was present. Normalize those bodies so the
 * real message appears on thrown errors and in app-level error strings.
 */
function wrapFetchForGeminiErrorBodies(
  fetchImpl: typeof globalThis.fetch,
): typeof globalThis.fetch {
  return async (input, init) => {
    const res = await fetchImpl(input, init);
    if (res.ok) return res;

    const text = await res.text();
    let parsed: unknown;
    try {
      parsed = text.trim() ? JSON.parse(text) : null;
    } catch {
      return new Response(text, {
        status: res.status,
        statusText: res.statusText,
        headers: res.headers,
      });
    }

    if (
      parsed &&
      typeof parsed === "object" &&
      !Array.isArray(parsed) &&
      !("error" in parsed)
    ) {
      const keys = Object.keys(parsed as Record<string, unknown>);
      const synthetic = {
        error: {
          message:
            keys.length === 0
              ? text || `HTTP ${res.status} (empty JSON object)`
              : JSON.stringify(parsed),
          type: "invalid_request_error",
        },
      };
      return new Response(JSON.stringify(synthetic), {
        status: res.status,
        statusText: res.statusText,
        headers: res.headers,
      });
    }

    return new Response(text, {
      status: res.status,
      statusText: res.statusText,
      headers: res.headers,
    });
  };
}

export const gemini = new OpenAI({
  apiKey,
  baseURL,
  fetch: wrapFetchForGeminiErrorBodies(globalThis.fetch.bind(globalThis)),
});
