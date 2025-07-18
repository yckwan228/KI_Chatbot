from typing import Optional
from fastapi import FastAPI
import os
from mistralai import Mistral
import logging
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)


app = FastAPI()

# 🔐 Mistral API-Key und Client
MISTRAL_API_KEY = "..."
client = Mistral(api_key=MISTRAL_API_KEY)

# 📄 Document Library Agent erstellen

library_agent = client.beta.agents.create(
    model="mistral-medium-2505",
    name="Document Library Agent",
    description="Agent used to access documents from the document library.",
    instructions="""Sie sind ein KI-gestützter Chatbot, der Fragen zu Stellenangeboten beantwortet und relevante Jobs basierend auf Stellenanzeigen-Daten vorschlägt. enn Stellenangebote sehr ähnlich klingen, analysiere Titel, Ort, Branche und Position genau, um die genaueste Übereinstimmung zu liefern.
    Nutze das Tool document_library, um passende Stellen zu finden. Gib danach die drei besten Stellenanzeigen als eine Liste zurück – mit Titel, Arbeitgeber, Ort, Anstellungsart, Branche/Fächer, Positionen, Arbeitsbereich, Art des Arbeitgebers, Arbeitszeit
""",
    tools=[{"type": "document_library", "library_ids": ["01980d53-277a-727b-a915-eea36d30105a"]}],  # <library_id> ersetzen
    completion_args={
        "temperature": 0.3,
        "top_p": 0.95,
    }
)

# 📜 Bestehende Conversations abrufen
@app.get("/conversations")
def list_conversations():
    try:
        conversations = client.beta.conversations.list()
        return {"conversations": [c.id for c in conversations]}
    except Exception as e:
        return {"error": str(e)}

class ChatInput(BaseModel):
    user_input: str
    conversation_id: Optional[str] = None

@app.post("/chat")
def chat_with_mistral(data: ChatInput):
    import time
    try:
        start_time = time.time()
        inputs = [{"role": "user", "content": data.user_input}]
        print("📥 Anfrage vom User:", inputs)
        print("📡 Starte Mistral Conversations API...")

        if data.conversation_id is None:
            response = client.beta.conversations.start(
                agent_id=library_agent.id,
                inputs=data.user_input
            )
            conversation_id = response.conversation_id
        else:
            response = client.beta.conversations.append(
                conversation_id=data.conversation_id,
                inputs=data.user_input
            )
            conversation_id = data.conversation_id

        print("💬 Conversation ID:", conversation_id)

        full_response = "Keine Antwort erhalten."
        if response and response.outputs:
            output = response.outputs[0]
            if hasattr(output, "content"):
                full_response = output.content
            elif hasattr(output, "text"):
                full_response = output.text
            elif hasattr(output, "type") and output.type == "tool.execution":
                print(f"[Tool-Ausführung erkannt]: {output.name} - {output.arguments}")
                # Warte auf Tool-Ausgabe durch stillen Folgeprompt
                followup = client.beta.conversations.append(
                    conversation_id=conversation_id,
                    inputs="Bitte gib die Ergebnisse der vorherigen Toolausführung aus."
                )
                if followup.outputs:
                    follow_output = followup.outputs[0]
                    if hasattr(follow_output, "content") or hasattr(follow_output, "text"):
                        raw_text = getattr(follow_output, "content", None) or getattr(follow_output, "text", "")
                        # Formatierung der Stellenanzeige-Antwort
                        import re
                        listings = re.split(r"(?:\n\s*)?(?=\d\.\s+\*\*)", raw_text.strip())
                        listings = [l for l in listings if l.strip() and not l.strip().startswith("**")]
                        formatted_response = ""
                        for listing in listings:
                            if not listing.strip():
                                continue
                            lines = listing.strip().split("\n")
                            details = {
                                "Titel": "",
                                "Arbeitgeber": "",
                                "Ort": "",
                                "Arbeitsort": "",
                                "Positionen": "",
                                "Branche/Fächer": "",
                                "Arbeitszeit": "",
                                "Anstellungsart": ""
                            }
                            # Vorzeitiges Überspringen von Listings ohne Inhalt
                            if all(not v.strip() for v in details.values()):
                                continue
                            for line in lines:
                                line = line.strip()
                                for key in details:
                                    if key in line:
                                        parts = line.split("**")
                                        if len(parts) > 1:
                                            details[key] = parts[-1].strip()
                                        else:
                                            details[key] = line.split(":")[-1].strip()
                                if line.startswith("**Titel:**"):
                                    details["Titel"] = line.replace("**Titel:**", "").strip("* ").strip()

                            formatted_response += (
                                f"\n• {details['Titel']}\n"
                                f"  • Arbeitgeber: {details['Arbeitgeber']}\n"
                                f"  • Ort / Arbeitsort: {details['Ort']} / {details['Arbeitsort']}\n"
                                f"  • Positionen: {details['Positionen']}\n"
                                f"  • Branche/Fächer: {details['Branche/Fächer']}\n"
                                f"  • Arbeitszeit: {details['Arbeitszeit']}\n"
                                f"  • Anstellungsart: {details['Anstellungsart']}\n"
                            )
                        full_response = formatted_response.strip() if formatted_response else raw_text
                    else:
                        full_response = "[Tool-Ausführung abgeschlossen – keine Ausgabe]"
                else:
                    full_response = "[Tool gestartet – aber keine Folgeantwort erhalten]"

        result = {
            "conversation_id": conversation_id,
            "response": full_response
        }
        duration = time.time() - start_time
        print(f"⏱️ Antwortzeit vom LLM: {duration:.2f} Sekunden")
        return result

    except Exception as e:
        return {"error": str(e)}


# Check Endpoint
@app.get("/")
def health_check():
    return {"status": "Backend läuft ✔️"}