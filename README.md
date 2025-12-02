# Whatsapp-Automation
# **Salon AI Booking Bot – n8n Workflow**  
*(WhatsApp ←→ OpenAI ←→ Google Sheets / Calendar)*

---

## **What it does**
- Listens to incoming WhatsApp messages (Twilio)  
- Detects intent (price, availability, cancel, etc.) and extracts slots (service, stylist, date, time, etc.)  
- Asks for missing info, then confirms the appointment in **markdown + a small JSON block**  
- On **“booking confirmed!!”**, it automatically:
  - Writes the row to Google Sheets  
  - Creates a Google Calendar event  
  - Sends the client a WhatsApp receipt including calendar link  
- Handles update / cancel flows  
- Uses a **10-message sliding-window memory** for a natural chat feel  

---

## **1. Prerequisites**
- n8n ≥ **1.38** (community or cloud)  
- Node.js code module enabled (`NODE_FUNCTION_ALLOW_EXTERNAL=*` if self-hosted)  
- Google Cloud project with **Calendar + Sheets APIs** enabled  
- Twilio account with a **WhatsApp-enabled sender** (your own number or Twilio sandbox)

---

## **2. One-click import**
1. Open **n8n → Workflows → “Import from file”**  
2. Choose **salon_booking.json**  
3. Deactivate the flow until credentials are connected

---

## **3. Credentials to create**

| Credential Type     | Name in Workflow         | How to Obtain |
|---------------------|---------------------------|----------------|
| **Twilio API**      | Twilio account 2          | Account SID + Auth Token (Twilio Console) |
| **OpenAI API**      | OpenAi account 2          | https://platform.openai.com → API key |
| **Google Sheets**   | Google Sheets account     | OAuth2 desktop flow (n8n wizard) |
| **Google Calendar** | Google Calendar account   | Same OAuth2 flow |

After import, n8n will ask to “fix” each credential — select the matching ones you created.

---

## **4. Environment variables**
Copy `.env.example` → `.env` (or paste in n8n Cloud → Variables):

```env
# ====== Required ======
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886      # Sandbox or your registered sender
GOOGLE_SHEETS_ID=1iOUZE7-yFr0AYz1wMXjRt7vVvEX_jskcIvoh3sTh2Zo
GOOGLE_CALENDAR_ID=floreshansharoldlee@gmail.com

# ====== Optional ======
NODE_FUNCTION_ALLOW_EXTERNAL=*      # for classifier code block
TZ=Asia/Manila                      # nicer timestamps
