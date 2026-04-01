"use client";

import { deleteDocument, activateDocument } from "@/lib/api";

const FILE_ICONS = {
  pdf: "📄",
  docx: "📝",
  xlsx: "📊",
  csv: "📋",
  pptx: "📑",
  default: "📁",
};

export default function DocumentList({
  documents,
  activeDocs,
  sessionId,
  onActivate,
  onDelete,
}) {
  async function handleActivate(doc) {
    console.log("Doc being activated:", doc); 
    try {
      await activateDocument(sessionId, doc.doc_id, doc.doc_name);
      onActivate(doc);
    } catch (err) {
      console.error("Activation failed", err);
    }
  }

  async function handleDelete(docId) {
    try {
      await deleteDocument(docId, sessionId);
      onDelete(docId);
    } catch (err) {
      console.error("Delete failed", err);
    }
  }

  function isActive(docId) {
    return activeDocs.some((d) => d.doc_id === docId);
  }

  function getIcon(fileType) {
    return FILE_ICONS[fileType] || FILE_ICONS.default;
  }

  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Library
      </p>

      {documents.length === 0 ? (
        <p className="text-xs text-gray-600 text-center mt-4">
          No documents uploaded yet
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              className={`rounded-lg px-3 py-2 border transition-all ${
                isActive(doc.doc_id)
                  ? "border-violet-500/30 bg-violet-500/5"
                  : "border-gray-800 bg-gray-900 hover:border-gray-700"
              }`}
            >
              <div className="flex items-center justify-between">
                {/* Doc info */}
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-sm shrink-0">
                    {getIcon(doc.file_type)}
                  </span>
                  <p className="text-xs text-gray-300 truncate">{doc.doc_name}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 ml-2 shrink-0">
                  {!isActive(doc.doc_id) ? (
                    <button
                      onClick={() => handleActivate(doc)}
                      className="text-xs text-gray-600 hover:text-violet-400 transition-colors"
                      title="Activate"
                    >
                      ▶
                    </button>
                  ) : (
                    <span className="text-xs text-violet-500" title="Active">
                      ●
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(doc.doc_id)}
                    className="text-xs text-gray-600 hover:text-red-400 transition-colors"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}