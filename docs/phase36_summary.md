# Phase 36 — your own model (0.36.0)

Last of the input-side arc (`plan_phases_31-36.md`). No schema change, no
prompt change, no static-file change. Shipped as **untested**: there's no
local model to try it against, so it was exercised against a fake
OpenAI-style server that replays the mock provider's replies.

## `OpenAICompatibleProvider` (`llm/providers.py`)
One HTTP POST to `{base}/chat/completions` with urllib; no SDK. Covers
Ollama, LM Studio, llama.cpp, vLLM and OpenRouter.
- `base_url` gets `/v1` when it has no path, so `http://host:11434` works.
- JSON mode sends `response_format: json_object`; a 400 retries once without
  it (older servers).
- Images go as `image_url` data URLs ahead of the text.
- A reasoning model's leading `<think>…</think>` is stripped.
- `last_usage` from `prompt_tokens` / `completion_tokens`;
  `last_finish_reason` from `finish_reason`. `"length"` already counts as
  truncation in `service._is_truncated`.
- `thinking` is ignored. Errors (no base URL, no model, unreachable server,
  HTTP errors with the server's message) raise `ProviderError`.
- Request timeout = `LLM_JOB_TIMEOUT_MINUTES`.

## Options
`llm_provider` gains `openai_compatible`. New `llm_base_url`, `llm_api_key`
(password), `llm_images` (bool, default false) and `llm_job_timeout_minutes`
(1–60, default 5). The last replaces the hard-coded `STALE_AFTER_SECONDS` in
the generation stale guard. `LLM_MODEL` is required for this provider (no
default); `LLM_QA_MODEL` falls back to it.

## Gating and copy
- `provider_reads_images()` returns `LLM_IMAGES` for this provider, so
  receipt scanning and *From a photo* are hidden for a text-only model.
- `provider_is_cloud()`: the receipt privacy line says "Your AI model reads
  this photo…" for this provider (it may be local or a cloud service),
  "A cloud AI model…" otherwise. Never a provider name.
- Usage: calls record `openai_compatible:<model>` with tokens. No price is on
  file, so the cost shows the existing "*" (the same provider can be a paid
  cloud service, so showing zero would be wrong).

## Docs
`DOCS.md` "Your own model (untested)": the untested caveat up front, the
options, and the weaker allergy adherence of small models. A Pi is too slow to
host one; use a GPU or Apple Silicon machine on the LAN. To check the wiring
yourself: Ollama with a small model on any PC, `llm_base_url` pointing at it.
