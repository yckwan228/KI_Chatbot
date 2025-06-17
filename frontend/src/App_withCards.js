
import './App_withCards.css';
import { useState, useEffect, useRef } from "react";
import JobCard from "./Jobcard";

function App() {
   const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket("ws://localhost:8000/ws/chat");

    ws.current.onmessage = (event) => {
      setIsTyping(false);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "assistant") {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...last,
            content: last.content + event.data
          };
          return updated;
        } else {
          return [...prev, { role: "assistant", content: event.data }];
        }
      });
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const sendMessage = () => {
    const userMsg = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    ws.current.send(input);
    setInput("");
    setIsTyping(true);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">Academics Karriere-Chatbot (Prototype)</div>
      <div className="chat-box">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            {(() => {
              try {
                const jsonStart = msg.content.indexOf("[");
                const jsonEnd = msg.content.lastIndexOf("]") + 1;
                const maybeJson = msg.content.slice(jsonStart, jsonEnd);
                const cleaned = maybeJson.replace(/\/\/.*$/gm, "");
                const data = JSON.parse(cleaned);
                if (Array.isArray(data)) {
                  console.log("✅ JSON aus Text extrahiert –", data.length, "Einträge");
                  return data.map((job, index) => <JobCard key={index} job={job} />);
                } else {
                  console.log("⚠️ JSON erkannt, aber kein Array:", data);
                }
              } catch (e) {
                console.log("❌ Keine JSON-Antwort:", msg.content);
              }
              return msg.content;
            })()}
          </div>
        ))}
        {isTyping && (
          <div className="chat-bubble assistant">
            <em>Der Bot schreibt gerade …</em>
          </div>
        )}
      </div>
      <div className="chat-input">
        <input
          type="text"
          placeholder="Ich suche nach..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>➤</button>
      </div>
    </div>
  );
}

export default App;
