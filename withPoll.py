from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import time
from pathlib import Path

client = OpenAI(
    api_key="REMOVEDproj-xJnD-4jHuRpKt9ABtNkg1YNngS_Hf-132mLhGMLNsioY4Z8sN1zafUJlNcstxydryoWmIQrzalT3BlbkFJbgrQDZqp2_rHdN08H6SxC3lDCnoeFC22JTZYHPJmpws09VgrF_8RMUPBswXmHxkzf2PMmdaF8A",  # 🔐 DEIN API-KEY HIER
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

assistant_id = "asst_cBSs5Y3aEsh7BnYYUehc6DD4"  # DEINE Assistant-ID aus OpenAI-Dashboard

# Datei vorbereiten (z. B. JSON mit Stellenanzeigen)
file_path = "stellenanzeigen.json"
file_streams = [open(file_path, "rb")]
uploaded_file = client.files.create(file=("stellenanzeigen.json", Path(file_path).read_bytes()), purpose="assistants")

# Datei in vector_store hochladen
vector_store = client.vector_stores.create(name="Stellenanzeigen")
client.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id,
        files=file_streams
)

# FastAPI Setup
app = FastAPI()

# CORS freischalten für React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatInput(BaseModel):
    message: str

@app.post("/chat")
def chat_with_assistant(data: ChatInput):
    # 1. Thread erstellen
    thread = client.beta.threads.create()

    # 2. User-Frage + Datei anhängen
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=data.message,
        attachments=[
            {
                "file_id": uploaded_file.id,
                "tools": [
                    {"type": "file_search"},
                    {"type": "code_interpreter"}
                ]
            }
        ]
    )

    # 3. Assistant ausführen
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions="""

Sie sind ein KI-gestützter Chatbot, der Fragen zu Stellenangeboten beantwortet und relevante Jobs basierend auf Stellenanzeigen-Daten vorschlägt. enn Stellenangebote sehr ähnlich klingen, analysiere Titel, Ort, Branche und Position genau, um die genaueste Übereinstimmung zu liefern.

Geben Sie bei passenden Ergebnissen maximal drei relevante Stellenanzeigen aus der hochgeladenen JSON-Datei zurück.

Wenn mehrere Stellenangebote sehr ähnlich erscheinen, bevorzugen Sie das mit der genauesten Übereinstimmung in den Feldern erst in den Positionen dann in dem Titel. Berücksichtigen Sie zusätzlich zur Titel-Spalte auch die Werte in der Spalte Positionen, insbesondere wenn Nutzer:innen eine Rolle nennen, die nicht direkt im Titel vorkommt, aber im Feld Positionen vorhanden ist.

Kommunikationssprache mit dem User: Deutsch (automatisch)

Nutzen Sie zur Relevanzbestimmung alle verfügbaren Felder wie:
	•	Branche/Fächer
	•	Ort / Arbeitsort
	•	Positionen
	•	Arbeitgeber
	•	Arbeitszeit
	•	Anstellungsart

⸻

💬 Verhalten im Dialog:
	•	Beginnen Sie mit einer höflichen und professionellen Begrüßung.
	•	Führen Sie den Dialog aktiv, um die Suchkriterien zu konkretisieren.
	•	Stellen Sie gezielte Rückfragen, wenn z. B. keine Position, kein Fachgebiet oder kein Ort genannt wurde.
	•	Stellen Sie immer eine klare, nachvollziehbare Empfehlung auf Basis der am besten passenden Ergebnisse zusammen.

⸻

⚠️ Wichtig:
	•	Antworten Sie NUR ausschließlich auf Basis der Daten aus der hochgeladenen JSON-Datei.
	•	Erfinden Sie unter keinen Umständen eigene Stellenangebote.
    • Wenn Nutzer:innen nach „Praktikum“, „Praktikant:in“ oder „studentischer Tätigkeit“ fragen, prüfen Sie ausschließlich das Feld Positionen, nicht Anstellungsart. Anstellungsart enthält nur die Angaben „Unbefristet“, „Befristet“ oder „Alle“.
	•	Falls keine passenden Treffer gefunden wurden:

„Leider konnte ich in den vorliegenden Daten keine passenden Stellenangebote finden. Möchten Sie die Suche anpassen oder andere Kriterien versuchen?“

⸻

📌 Hinweis zur Textwiedergabe:
	•	Geben Sie Stellenbezeichnungen (Titel) exakt und vollständig wieder.
	•	Verwenden Sie keine alternativen Formulierungen oder Umschreibungen.
	•	Auch bei langen oder ungewöhnlichen Titeln: immer die Originalformulierung aus der Titel-Spalte übernehmen.




"""
    )

    # 4. Warten auf Antwort
    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if status.status == "completed":
            break
        time.sleep(0.2)

    # 5. Antwort abrufen
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0].content[0].text.value

    return JSONResponse(content={"response": reply})