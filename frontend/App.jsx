import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const res = await axios.post("http://localhost:8000/chat", {
        message: input,
      });
      const assistantMessage = { role: "assistant", content: res.data.response };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMsg = { role: "assistant", content: "❌ Fehler: " + err.message };
      setMessages((prev) => [...prev, errorMsg]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="chat-container">
      <div className="chat-header">💼 Karriere-Chatbot</div>

      <div className="chat-box">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>

      <div className="chat-input">
        <input
          type="text"
          placeholder="Nachricht eingeben..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button onClick={sendMessage}>➤</button>
      </div>
    </div>
  );
}

export default App;