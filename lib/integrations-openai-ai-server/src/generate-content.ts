/**
 * Native Gemini REST API: `generateContent` (not the OpenAI-compatible surface).
 * @see https://ai.google.dev/api/rest/v1beta/models/generateContent
 */

const DEFAULT_NATIVE_BASE = "https://generativelanguage.googleapis.com/v1beta";

export interface GenerateContentTextOptions {
  /** e.g. `gemini-flash-latest` — overrides env for this call */
  model?: string;
  maxOutputTokens?: number;
}

function textFromGenerateContentResponse(json: unknown): string {
  const root = json as {
    candidates?: Array<{
      content?: { parts?: Array<{ text?: string }> };
      finishReason?: string;
    }>;
    promptFeedback?: { blockReason?: string };
    error?: { code?: number; message?: string; status?: string };
  };

  if (root.error) {
    const msg = root.error.message ?? JSON.stringify(root.error);
    throw new Error(`Gemini API error: ${msg}`);
  }

  if (root.promptFeedback?.blockReason) {
    throw new Error(
      `Gemini blocked the prompt: ${root.promptFeedback.blockReason}`,
    );
  }

  const candidates = root.candidates;
  if (!candidates?.length) {
    throw new Error("Gemini returned no candidates (empty response).");
  }

  const parts = candidates[0]?.content?.parts;
  if (!parts?.length) {
    throw new Error(
      `Gemini returned no text parts (finish: ${candidates[0]?.finishReason ?? "unknown"}).`,
    );
  }

  return parts.map((p) => p.text ?? "").join("");
}

/**
 * Calls `POST .../models/{model}:generateContent` with `X-goog-api-key`.
 */
export async function generateContentText(
  prompt: string,
  options?: GenerateContentTextOptions,
): Promise<string> {
  const apiKey = process.env.GEMINI_API_KEY?.trim();
  if (!apiKey) {
    throw new Error(
      "GEMINI_API_KEY must be set. Create a key in Google AI Studio: https://aistudio.google.com/apikey",
    );
  }

  const base =
    process.env.GEMINI_NATIVE_API_BASE?.trim() || DEFAULT_NATIVE_BASE;
  const model =
    options?.model?.trim() ||
    process.env.BIM_EXTRACTION_MODEL?.trim() ||
    "gemini-flash-latest";

  const url = `${base.replace(/\/$/, "")}/models/${encodeURIComponent(model)}:generateContent`;

  const body = {
    contents: [
      {
        parts: [{ text: prompt }],
      },
    ],
    generationConfig: {
      maxOutputTokens: options?.maxOutputTokens ?? 8192,
    },
  };

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-goog-api-key": apiKey,
    },
    body: JSON.stringify(body),
  });

  const raw = await res.text();
  let json: unknown;
  try {
    json = raw.trim() ? JSON.parse(raw) : null;
  } catch {
    throw new Error(
      `Gemini generateContent failed (HTTP ${res.status}): invalid JSON body: ${raw.slice(0, 500)}`,
    );
  }

  if (!res.ok) {
    const errObj = json as { error?: { message?: string } } | null;
    const detail =
      (errObj?.error?.message ??
        (typeof json === "object" && json !== null
          ? JSON.stringify(json)
          : raw)) || "(no body)";
    throw new Error(
      `Gemini generateContent failed (HTTP ${res.status}): ${detail}`,
    );
  }

  if (json === null || typeof json !== "object") {
    throw new Error("Gemini generateContent: empty or invalid response.");
  }

  return textFromGenerateContentResponse(json);
}
