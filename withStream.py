from fastapi import WebSocket, WebSocketDisconnect
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import time
from pathlib import Path
from typing_extensions import override
from openai import AssistantEventHandler
import asyncio

client = OpenAI(
    api_key="REMOVED...",
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

assistant_id = "asst_cBSs5Y3aEsh7BnYYUehc6DD4"  # DEINE Assistant-ID aus OpenAI-Dashboard

assistant = client.beta.assistants.retrieve(assistant_id)


# Datei vorbereiten (z. B. JSON mit Stellenanzeigen)
file_path = "stellenanzeigen.json"
file_streams = [open(file_path, "rb")]
uploaded_file = client.files.create(file=("stellenanzeigen.json", Path(file_path).read_bytes()), purpose="assistants")

# Datei in vector_store hochladen
vector_store = client.vector_stores.create(name="Stellenanzeigen-Experte_V1")
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

class EventHandler(AssistantEventHandler):    
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
        
    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        
    def on_tool_call_created(self, tool_call):
        print("Assistant verwendet Tool:", tool_call.type, flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)

@app.post("/chat")
def chat_with_assistant(data: ChatInput):
    if not hasattr(chat_with_assistant, "thread_id"):
        thread = client.beta.threads.create(
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                },
                "code_interpreter": {
                    "file_ids": [uploaded_file.id]
                }
            }
        )
        chat_with_assistant.thread_id = thread.id
    else:
        thread = client.beta.threads.retrieve(chat_with_assistant.thread_id)

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

    start_time = time.time()
    # 3. Assistant ausführen
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions="""

Sie sind ein KI-gestützter Chatbot, der Fragen zu Stellenangeboten beantwortet und relevante Jobs basierend auf Stellenanzeigen-Daten vorschlägt. enn Stellenangebote sehr ähnlich klingen, analysiere Titel, Ort, Branche und Position genau, um die genaueste Übereinstimmung zu liefern.

Geben Sie bei passenden Ergebnissen maximal drei relevante Stellenanzeigen aus der hochgeladenen JSON-Datei zurück.

Wenn mehrere Stellenangebote sehr ähnlich erscheinen, bevorzugen Sie das mit der genauesten Übereinstimmung in den Feldern erst in den Positionen dann in dem Titel. Berücksichtigen Sie zusätzlich zur Titel-Spalte auch die Werte in der Spalte Positionen, insbesondere wenn Nutzer:innen eine Rolle nennen, die nicht direkt im Titel vorkommt, aber im Feld Positionen vorhanden ist.

Kommunikationssprache mit dem User: Deutsch (automatisch)

Fragen Sie gerne am Anfang des Chats nach: Positionen, Arbeitsorte und Branche/Fächer.

Nutzen Sie zur Relevanzbestimmung alle verfügbaren Felder wie:
	•	Branche/Fächer
	•	Ort / Arbeitsort
	•	Positionen
	•	Arbeitgeber
	•	Arbeitszeit
	•	Anstellungsart

⸻

Zurückgeben Sie die gefundenen Stellen in diesem Muster:

    •	Titel
    •	Arbeitgeber
    •	Ort / Arbeitsort
	•	Positionen
	•	Branche/Fächer
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
    •   „Bereich“ kann stellvertretend für Fachrichtung, Fachgebiet, Branche oder Fächer verstanden werden.
    •   Wenn Nutzer:innen nach „Praktikum“, „Praktikant:in“ oder „studentischer Tätigkeit“ fragen, prüfen Sie ausschließlich das Feld Positionen, nicht Anstellungsart. Anstellungsart enthält nur die Angaben „Unbefristet“, „Befristet“ oder „Alle“.
	•	Falls keine passenden Treffer gefunden wurden:

„Leider konnte ich in den vorliegenden Daten keine passenden Stellenangebote finden. Möchten Sie die Suche anpassen oder andere Kriterien versuchen?“

⸻

📌 Hinweis zur Textwiedergabe:
	•	Geben Sie Stellenbezeichnungen (Titel) exakt und vollständig wieder.
	•	Verwenden Sie keine alternativen Formulierungen oder Umschreibungen.
	•	Auch bei langen oder ungewöhnlichen Titeln: immer die Originalformulierung aus der Titel-Spalte übernehmen.

""",
        event_handler=EventHandler(),
    ) as stream:
        stream.until_done()
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    print("⏱️ Antwortdauer:", duration, "Sekunden")
        
    return JSONResponse(content={"response": "[streamed to console]"})


# WebSocket-Endpoint für Chat
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            if not hasattr(websocket_chat, "thread_id"):
                thread = client.beta.threads.create(
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [vector_store.id]
                        },
                        "code_interpreter": {
                            "file_ids": [uploaded_file.id]
                        }
                    }
                )
                websocket_chat.thread_id = thread.id
            else:
                thread = client.beta.threads.retrieve(websocket_chat.thread_id)
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=data,
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

            # Event-Handler → stream live zum WebSocket
            class WSHandler(AssistantEventHandler):
                @override
                def on_text_delta(self, delta, snapshot):
                    asyncio.create_task(websocket.send_text(delta.value))
                def on_tool_call_created(self, tool_call):
                    print("Assistant verwendet Tool (WebSocket):", tool_call.type, flush=True)

            start_time = time.time()
            with client.beta.threads.runs.stream(
                thread_id=thread.id,
                assistant_id=assistant_id,
                instructions="""


Sie sind ein KI-gestützter Chatbot, der Fragen zu Stellenangeboten beantwortet und relevante Jobs basierend auf Stellenanzeigen-Daten vorschlägt. enn Stellenangebote sehr ähnlich klingen, analysiere Titel, Ort, Branche und Position genau, um die genaueste Übereinstimmung zu liefern.

Geben Sie bei passenden Ergebnissen maximal drei relevante Stellenanzeigen aus der hochgeladenen JSON-Datei zurück.

Wenn mehrere Stellenangebote sehr ähnlich erscheinen, bevorzugen Sie das mit der genauesten Übereinstimmung in den Feldern erst in den Positionen dann in dem Titel. Berücksichtigen Sie zusätzlich zur Titel-Spalte auch die Werte in der Spalte Positionen, insbesondere wenn Nutzer:innen eine Rolle nennen, die nicht direkt im Titel vorkommt, aber im Feld Positionen vorhanden ist.

Kommunikationssprache mit dem User: Deutsch (automatisch)

Fragen Sie gerne am Anfang des Chats nach: Positionen, Arbeitsorte und Branche/Fächer.

Nutzen Sie zur Relevanzbestimmung alle verfügbaren Felder wie:
	•	Branche/Fächer
	•	Ort / Arbeitsort
	•	Positionen
	•	Arbeitgeber
	•	Arbeitszeit
	•	Anstellungsart

⸻

Zurückgeben Sie die gefundenen Stellen in diesem Muster:

    •	Titel
    •	Arbeitgeber
    •	Ort / Arbeitsort
	•	Positionen
	•	Branche/Fächer
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
    •   „Bereich“ kann stellvertretend für Fachrichtung, Fachgebiet, Branche oder Fächer verstanden werden.
    •   Wenn Nutzer:innen nach „Praktikum“, „Praktikant:in“ oder „studentischer Tätigkeit“ fragen, prüfen Sie ausschließlich das Feld Positionen, nicht Anstellungsart. Anstellungsart enthält nur die Angaben „Unbefristet“, „Befristet“ oder „Alle“.
	•	Falls keine passenden Treffer gefunden wurden:

„Leider konnte ich in den vorliegenden Daten keine passenden Stellenangebote finden. Möchten Sie die Suche anpassen oder andere Kriterien versuchen?“

⸻

📌 Hinweis zur Textwiedergabe:
	•	Geben Sie Stellenbezeichnungen (Titel) exakt und vollständig wieder.
	•	Verwenden Sie keine alternativen Formulierungen oder Umschreibungen.
	•	Auch bei langen oder ungewöhnlichen Titeln: immer die Originalformulierung aus der Titel-Spalte übernehmen.

""",
                event_handler=WSHandler(),
            ) as stream:
                stream.until_done()
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            print("Antwortdauer:", duration, "Sekunden")

    except WebSocketDisconnect:
        print("Client disconnected")
        print("Assistant verwendet Modell:", assistant.model)