"use client";
import { useState, useRef, useEffect } from "react";
import { sendChatMessage, ChatResponse } from "../lib/api";

interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  actions?: ChatResponse;
}

interface ChatPanelProps {
  onTradeExecuted: () => void;
  onWatchlistChange: () => void;
}

export default function ChatPanel({ onTradeExecuted, onWatchlistChange }: ChatPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const response = await sendChatMessage(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.message, actions: response },
      ]);
      if (response.trades_executed?.length > 0) onTradeExecuted();
      if (response.watchlist_changes?.length > 0) onWatchlistChange();
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
      ]);
    }
    setLoading(false);
  };

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-[#1a1a2e] border border-[#21262d] text-[#ecad0a] px-1 py-4 rounded-l text-xs writing-mode-vertical"
        style={{ writingMode: "vertical-rl" }}
      >
        Chat
      </button>
    );
  }

  return (
    <div className="flex flex-col h-full border-l border-[#21262d]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#21262d]">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Chat</span>
        <button onClick={() => setCollapsed(true)} className="text-gray-500 hover:text-white text-xs">
          &times;
        </button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-2 space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[90%] rounded px-3 py-2 text-xs ${
                m.role === "user"
                  ? "bg-[#209dd7]/20 text-white"
                  : "bg-[#1a1a2e] text-gray-300"
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              {m.actions?.trades_executed && m.actions.trades_executed.length > 0 && (
                <div className="mt-1 pt-1 border-t border-[#21262d]">
                  {m.actions.trades_executed.map((t, j) => (
                    <div key={j} className="text-[#ecad0a] text-xs">
                      {t.side === "buy" ? "Bought" : "Sold"} {t.quantity} {t.ticker} @ ${t.price}
                    </div>
                  ))}
                </div>
              )}
              {m.actions?.watchlist_changes && m.actions.watchlist_changes.length > 0 && (
                <div className="mt-1 pt-1 border-t border-[#21262d]">
                  {m.actions.watchlist_changes.map((w, j) => (
                    <div key={j} className="text-[#209dd7] text-xs">
                      {w.action === "add" ? "Added" : "Removed"} {w.ticker} {w.action === "add" ? "to" : "from"} watchlist
                    </div>
                  ))}
                </div>
              )}
              {m.actions?.errors && m.actions.errors.length > 0 && (
                <div className="mt-1 pt-1 border-t border-[#21262d]">
                  {m.actions.errors.map((e, j) => (
                    <div key={j} className="text-[#f85149] text-xs">{e}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#1a1a2e] rounded px-3 py-2 text-xs text-gray-400 animate-pulse">
              Thinking...
            </div>
          </div>
        )}
      </div>
      <div className="flex border-t border-[#21262d] p-2 gap-1">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask FinAlly..."
          className="flex-1 bg-[#1a1a2e] text-white text-xs px-2 py-1.5 rounded border border-[#21262d] outline-none focus:border-[#209dd7]"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-[#753991] text-white text-xs px-3 py-1.5 rounded font-semibold hover:brightness-110 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
