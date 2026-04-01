"use client";

import SourceCard from "./SourceCard";

export default function SourcePanel({ sources }) {
  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300">Sources</h2>
        <p className="text-xs text-gray-600 mt-0.5">
          {sources.length > 0
            ? `${sources.length} sources retrieved`
            : "No sources yet"}
        </p>
      </div>

      {/* Sources List */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {sources.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-xs text-gray-600 text-center">
              Sources will appear here after your first query
            </p>
          </div>
        ) : (
          sources.map((source, i) => (
            <SourceCard key={i} source={source} index={i + 1} />
          ))
        )}
      </div>
    </div>
  );
}
