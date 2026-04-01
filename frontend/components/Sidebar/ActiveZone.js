"use client";

import { deactivateDocument } from "@/lib/api";

export default function ActiveZone({ activeDocs, sessionId, onDeactivate }) {

  async function handleDeactivate(docId) {
    try {
      await deactivateDocument(sessionId, docId);
      onDeactivate(docId);
    } catch (err) {
      console.error("Deactivation failed", err);
    }
  }

  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Active Knowledge
      </p>

      {activeDocs.length === 0 ? (
        <div className="border border-dashed border-gray-800 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-600">No active documents</p>
          <p className="text-xs text-gray-700 mt-0.5">Activate from library below</p>
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {activeDocs.map((doc) => (
            <div
              key={doc.doc_id}
              className="flex items-center justify-between bg-violet-500/10 border border-violet-500/20 rounded-lg px-3 py-2"
            >
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                <p className="text-xs text-violet-300 truncate">{doc.doc_name}</p>
              </div>
              <button
                onClick={() => handleDeactivate(doc.doc_id)}
                className="text-gray-600 hover:text-red-400 transition-colors ml-2 shrink-0"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}