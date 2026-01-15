import json
from openai import OpenAI
from typing import Dict, Any, List

# -----------------------------
# OpenAI client
# -----------------------------

client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://your-domain-or-app-name",
        "X-Title": "Credit Analysis Bot"
    }
)

# -----------------------------
# Optimized system prompt
# -----------------------------

SYSTEM_PROMPT = """
You are a UK FCA consumer credit and irresponsible lending analyst.

You must analyse only the information provided.
Do not invent lenders, dates, facts, or outcomes.

Apply FCA CONC affordability principles and established irresponsible lending standards.

Your tasks:
- Analyse IN-SCOPE lenders for potential irresponsible lending
- Explain why OUT-OF-SCOPE entities cannot be pursued

Rules:
- Base conclusions strictly on risk indicators present at the point of lending
- Treat sub-prime lenders differently where relevant
- Do not repeat the data verbatim
- Do not speculate
- Use clear, professional legal reasoning

Output format:

In-Scope: Potential Claims
<short explanation>

<Lender Name>

<Account Type>
<reasoned analysis>

---

Out-of-Scope: Not Defendants
<short explanation>

<Entity Name>

<Entity Type>
<reason excluded>
"""

# -----------------------------
# JSON pre-processor
# -----------------------------

def prepare_ai_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    claims = raw.get("claims_analysis", {})

    in_scope_accounts: List[Dict[str, Any]] = []
    for acc in claims.get("in_scope_accounts", []):
        in_scope_accounts.append({
            "lender": acc["lender"],
            "account_type": acc["account_type"],
            "start_date": acc["start_date"],
            "default_date": None if acc["default_date"] == "N/A" else acc["default_date"],
            "is_subprime_lender": acc.get("is_subprime_lender", False),
            "risk_at_lending": {
                "active_ccjs": acc["risk_indicators_at_lending"]["active_ccjs_at_lending"],
                "active_defaults": acc["risk_indicators_at_lending"]["active_defaults_at_lending"],
                "accounts_in_arrears": acc["risk_indicators_at_lending"]["accounts_in_arrears_at_lending"],
                "debt_collection_accounts": acc["risk_indicators_at_lending"]["debt_collection_accounts_active"]
            }
        })

    out_of_scope_accounts: List[Dict[str, Any]] = []
    for acc in claims.get("out_of_scope_accounts", []):
        out_of_scope_accounts.append({
            "lender": acc["lender"],
            "entity_type": acc["account_type"],
            "exclusion_reason": acc["exclusion_reason"]
        })

    summary_flags = {
        key: value["flagged"]
        for key, value in raw.get("indicators", {}).items()
        if value.get("flagged") is True
    }

    return {
        "client_name": raw["client_info"]["name"],
        "summary_flags": summary_flags,
        "in_scope_accounts": in_scope_accounts,
        "out_of_scope_accounts": out_of_scope_accounts
    }

# -----------------------------
# AI analysis function
# -----------------------------

def run_ai_analysis(clean_payload: Dict[str, Any]) -> str:
    response = client.chat.completions.create(
        model="gpt-oss-120b",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(clean_payload, indent=2)
            }
        ]
    )

    return response.choices[0].message.content.strip()

# -----------------------------
# End-to-end helper
# -----------------------------

def analyse_credit_report(raw_json: Dict[str, Any]) -> str:
    clean_payload = prepare_ai_payload(raw_json)
    return run_ai_analysis(clean_payload)

# -----------------------------
# Example usage
# -----------------------------

if __name__ == "__main__":
    with open("credit_report.json", "r", encoding="utf-8") as f:
        raw_report = json.load(f)

    analysis_output = analyse_credit_report(raw_report)
    print(analysis_output)
