"use client";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-violet-600 text-white rounded-tr-sm"
            : "bg-gray-900 text-gray-200 rounded-tl-sm border border-gray-800"
        }`}
      >
        {/* Message content */}
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </p>

        {/* Citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-700 flex flex-wrap gap-1.5">
            {message.sources.map((source, i) => (
              <span
                key={i}
                className={`text-xs px-2 py-0.5 rounded-full ${
                  source.from_cache
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : "bg-violet-500/10 text-violet-400 border border-violet-500/20"
                }`}
                title={`Score: ${source.score}`}
              >
                {source.doc_name} · p{source.page_num || "?"}
                {source.type === "image" && " · img"}
                {source.from_cache && " · cached"}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}