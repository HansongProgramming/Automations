import base64
import json
import requests
from config import OPENAI_API_KEY, OPENAI_API_URL, MODEL

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

def png_to_data_url(png_bytes):
    b64 = base64.b64encode(png_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def describe_images(images):
    """
    images: list of PNG bytes
    returns: combined AI text
    """

    content = [
        {
            "type": "input_text",
            "text": """
    You are acting as a housing disrepair surveyor preparing a photo-based triage report for Housing Disrepair Claims (England & Wales).
    There is no need to include a title.

    Produce structured, professional triage-style analysis.

    For EACH room (Include Image Range Example: Bathroom Images 1–8):

    1. Visible Damage
    2. Likely Causation (non-definitive)
    3. Scope of Impact
    4. If there is no damage, do not include the room / place

    Constraints:
    - No legal conclusions
    - No tenant health references
    - Evidence-based only
    - Add estimated costings and total per room in UK Pounds
    - At the end of the document add a horizontal line and include the overall total cost in UK Pounds
    - Format the output in straight HTML (do not use ```html```)
    - No need for <html> or <body> tags
    - Use headers, paragraphs, and lists only
    - Indent list items for readability
    - Strictly Follow the format provided

    Example format per room:

    <h4>ROOM 1 – Bathroom</h4>
    <h4>(Photographic Appendices 1–5)</h4>
    <h4>Visible Damage</h4>
    <ul>
        <li>Mould on bathtub, visible along silicone sealant and lower wall tiles</li>
        <li>Cracking on ceiling, including hairline crack extending to wall junction</li>
    </ul>

    <h4>Likely Causation (photo-supported only)</h4>
    <ul>
        <li>
            Ceiling staining, mould, and blistering are consistent with water ingress from above, supported by the concentration
            of damage around the ceiling and light fitting.
        </li>
    </ul>

    <h4>Estimated Costings</h4>
    <ul>
        <li>Mould treatment and biocidal wash to ceiling and walls: <strong>£80</strong></li>
    </ul>

    <h4>Bathroom Total: £80</h4>
    <hr>

    """
        }
    ]


    for img in images:
        content.append({
            "type": "input_image",
            "image_url": png_to_data_url(img)
        })

    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "user",
                "content": content
            }
        ]
    }

    response = requests.post(
        OPENAI_API_URL,
        headers=HEADERS,
        data=json.dumps(payload),
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    result = response.json()

    output_text = []
    for item in result.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                output_text.append(c.get("text"))

    return "\n".join(output_text).strip()
