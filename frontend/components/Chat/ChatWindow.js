"use client";

import { useState, useRef, useEffect } from "react";
import { queryDocuments, getSessionId } from "@/lib/api";
import MessageBubble from "./MessageBubble.js";
import ChatInput from "./ChatInput";

export default function ChatWindow({ onSourcesUpdate }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const sessionId = getSessionId();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleQuery(question) {
  if (!question.trim()) return;

  setMessages((prev) => [...prev, { role: "user", content: question }]);
  setLoading(true);

  // Add empty assistant message that will be filled as stream comes in
  setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

  try {
    await queryDocuments(
      question,
      sessionId,
      null,
      messages,
      // onChunk — append each chunk to last message
      (chunk) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = {
            ...last,
            content: last.content + chunk
          };
          return updated;
        });
      },
      // onSources — update sources when received
      (sources) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, sources };
          return updated;
        });
        onSourcesUpdate(sources);
      }
    );
  } catch (err) {
    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = {
        role: "assistant",
        content: "Something went wrong. Please try again.",
        sources: []
      };
      return updated;
    });
  } finally {
    setLoading(false);
  }
}

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300">Research Chat</h2>
        <p className="text-xs text-gray-600 mt-0.5">
          Ask anything about your documents
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <p className="text-2xl font-bold text-gray-700">Ragverse</p>
            <p className="text-sm text-gray-600 mt-2">
              Upload documents and start asking questions
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex gap-1.5 items-center">
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" />
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce delay-100" />
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce delay-200" />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-800">
        <ChatInput onSubmit={handleQuery} loading={loading} />
      </div>
    </div>
  );
}
