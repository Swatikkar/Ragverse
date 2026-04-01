"use client";

import { useState } from "react";

export default function ChatInput({ onSubmit, loading }) {
  const [question, setQuestion] = useState("");

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleSubmit() {
    if (!question.trim() || loading) return;
    onSubmit(question);
    setQuestion("");
  }

  return (
    <div className="flex items-end gap-3">
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything about your documents..."
        rows={1}
        className="flex-1 bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-violet-500 transition-colors"
      />
      <button
        onClick={handleSubmit}
        disabled={loading || !question.trim()}
        className="bg-violet-600 hover:bg-violet-500 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-xl px-4 py-3 text-sm font-medium transition-colors shrink-0"
      >
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
}