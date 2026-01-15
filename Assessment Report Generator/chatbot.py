import json
from openai import OpenAI
from typing import Dict, Any, List
from dotenv import load_dotenv
load_dotenv()  # loads .env into environment
import os

# -----------------------------
# OpenAI client
# -----------------------------

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
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

Output format must be in json not markdown:
{
  "in_scope": [
    {
      "name": "Capital One (Europe) PLC",
      "entity_type": "Credit Card",
      "reason_title": "Lending during adverse credit period",
      "reason_summary": "Extended credit while active defaults were visible on the credit file, indicating financial distress at the point of lending and a failure to conduct adequate affordability checks."
    }
  ],
  "out_of_scope": [
    {
      "name": "Lowell Portfolio I Ltd",
      "entity_type": "Debt Purchaser",
      "reason_title": "Not original lender",
      "reason_summary": "Debt purchaser and collection agency. Did not originate the credit agreement and therefore cannot be pursued for irresponsible lending or affordability failures."
    }
  ]
}

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
