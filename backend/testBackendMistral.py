import requests

API_URL = "http://localhost:8000/chat"
conversation_id = None

print("🔌 Verbinde zu", API_URL)
print("✅ Verbunden. Tippe deinen Prompt (oder 'exit' zum Beenden):")

while True:
    prompt = input("📝 Prompt: ")
    if prompt.lower() in {"exit", "quit", "q"}:
        print("👋 Verbindung wird beendet...")
        break

    payload = {
        "user_input": prompt,
        "conversation_id": conversation_id
    }

    try:
        response = requests.post(API_URL, json=payload)
        data = response.json()

        if "error" in data:
            print("⚠️ Fehler vom Server:", data["error"])
        else:
            print("🧠 Antwort vom Bot:", data["response"])
            conversation_id = data["conversation_id"]
            print("💬 Conversation ID:", conversation_id)
    except Exception as e:
        print("❌ Anfrage fehlgeschlagen:", e)