import json
import re

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.llm_output import LLMAnalysis
from app.services.llm.base import LLMUnavailableError
from app.services.llm.ollama_cloud import OllamaCloudProvider
from app.services.llm.ollama_local import OllamaLocalProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a Tier-1 SOC (Security Operations Center) investigation assistant.

You will be given evidence gathered by deterministic tools, clearly labeled by category:
- EVIDENCE: what the system directly observed in logs. This is ground truth.
- THREAT_INTELLIGENCE: information from threat intel providers about indicators (IPs, domains).
- KNOWLEDGE: reference material retrieved from a security knowledge base (investigation and response
  playbooks, MITRE ATT&CK, OWASP, NIST, CWE). Every item has an id such as [K1].
- RISK: a deterministic risk score already computed by a separate risk engine.

Your job is to analyze this evidence and produce a structured JSON assessment.

STRICT RULES - you must follow these exactly:
1. NEVER invent log events, timestamps, IP reputations, CVEs, or threat intelligence that was not
   provided to you in the evidence above.
2. NEVER claim a containment or response action was executed. You may only RECOMMEND actions; a human
   analyst must approve and execute them.
3. NEVER assume compromise without direct evidence. If the evidence is ambiguous or insufficient, set
   "insufficient_evidence" to true and explain what is missing in the summary.
4. Base "severity" and "confidence" on the evidence and the provided risk score - do not contradict a
   strong deterministic risk score without a clear evidence-based reason.
5. Only include a "mitre_technique" or "owasp_category" if it is clearly justified by the evidence and
   knowledge provided; otherwise leave it null.
6. Be CONCISE so the full response fits a limited token budget: "summary" max 2 sentences, "evidence"
   at most 4 short bullet points, "recommended_actions" at most 5 short bullet points, "threat_context"
   and "impact" one sentence each.
7. In "references", list the [K] ids of the KNOWLEDGE items your analysis and recommended actions are
   based on (e.g. ["K1", "K4"]). Only cite ids that appear above; never invent sources. Prefer the
   RESPONSE_PLAYBOOK items when recommending actions.
8. Respond with ONLY a single valid JSON object matching this exact schema, no markdown, no commentary:

{
  "attack_type": "string - short name of the attack/activity type",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL|UNKNOWN",
  "confidence": 0.0-1.0,
  "summary": "1-3 sentence plain-English summary of what happened",
  "evidence": ["short evidence bullet points, drawn only from the EVIDENCE provided"],
  "threat_context": "summary of relevant threat intelligence, or empty string if none",
  "impact": "brief statement of potential impact",
  "mitre_technique": "e.g. T1110, or null",
  "owasp_category": "e.g. A07:2021, or null",
  "recommended_actions": ["specific recommended response actions, never phrased as already done"],
  "requires_human_approval": true,
  "insufficient_evidence": false,
  "references": ["K ids of the knowledge items used, e.g. K1"]
}
"""


def _get_provider():
    if settings.LLM_PROVIDER == "ollama_cloud":
        # With a REST API key, call ollama.com directly. Otherwise run the
        # cloud model (e.g. gpt-oss:120b-cloud) through the local daemon,
        # which forwards it using the `ollama signin` session.
        if settings.OLLAMA_CLOUD_API_KEY:
            return OllamaCloudProvider()
        return OllamaLocalProvider(model=settings.OLLAMA_CLOUD_MODEL)
    return OllamaLocalProvider()


def _extract_json(text: str) -> dict:
    # Defensive: some reasoning models still emit a <think>...</think>
    # preamble even when asked not to. Strip it before looking for JSON.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError("No JSON object found in LLM response", text, 0)


def is_llm_available() -> bool:
    try:
        return _get_provider().is_available()
    except Exception:  # noqa: BLE001
        return False


def generate_structured_analysis(evidence_prompt: str) -> tuple[LLMAnalysis | None, str | None]:
    """Returns (analysis, error_message). Exactly one will be None."""
    provider = _get_provider()

    last_error = None
    for attempt in range(2):
        try:
            # json_mode=False: Ollama's strict format="json" grammar decoding
            # is incompatible with Qwen3's "/no_think" directive (produces
            # empty output). The system prompt already demands JSON-only
            # output, and _extract_json()/Pydantic validation below handle
            # the rest, with a retry on malformed output.
            raw = provider.generate(evidence_prompt, system=SYSTEM_PROMPT, json_mode=False)
        except LLMUnavailableError as exc:
            return None, str(exc)

        try:
            parsed = _extract_json(raw)
            analysis = LLMAnalysis(**parsed)
            return analysis, None
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = f"Malformed LLM output (attempt {attempt + 1}): {exc}"
            logger.warning(last_error)
            continue

    return None, last_error or "LLM output validation failed"
