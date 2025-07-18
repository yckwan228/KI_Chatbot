import logo from './logo.svg';
import './App.css';
import axios from "axios";
import { useState, useEffect, useRef } from "react";


function App() {
   const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket("ws://localhost:8000/ws/chat");

    ws.current.onmessage = (event) => {
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
  };

  return (
    <div className="chat-container">
      <div className="chat-header">Academics Karriere-Chatbot (Prototype)</div>
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