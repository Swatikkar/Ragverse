"use client";

import { useState, useEffect } from "react";
import FileUploader from "./FileUploader";
import ActiveZone from "./ActiveZone";
import DocumentList from "./DocumentList";
import { getDocuments, getSessionId } from "@/lib/api";

export default function Sidebar() {
  const [documents, setDocuments] = useState([]);
  const [activeDocs, setActiveDocs] = useState([]);
  const sessionId = getSessionId();

  useEffect(() => {
  async function fetchDocuments() {
    try {
      const res = await getDocuments();
      setDocuments(res.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    }
  }
  fetchDocuments();
}, []);

  function handleDocumentUploaded(newDoc) {
    setDocuments((prev) => [...prev, newDoc]);
  }

  function handleActivate(doc) {
    if (activeDocs.find((d) => d.doc_id === doc.doc_id)) return;
    setActiveDocs((prev) => [...prev, doc]);
  }

  function handleDeactivate(docId) {
    setActiveDocs((prev) => prev.filter((d) => d.doc_id !== docId));
  }

  function handleDelete(docId) {
    setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    handleDeactivate(docId);
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Logo */}
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">
          Rag<span className="text-violet-500">verse</span>
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">Multimodal Research Assistant</p>
      </div>

      {/* File Uploader */}
      <div className="p-3 border-b border-gray-800">
        <FileUploader
          sessionId={sessionId}
          onUploaded={handleDocumentUploaded}
        />
      </div>

      {/* Active Zone */}
      <div className="p-3 border-b border-gray-800">
        <ActiveZone
          activeDocs={activeDocs}
          sessionId={sessionId}
          onDeactivate={handleDeactivate}
        />
      </div>

      {/* Document Library */}
      <div className="flex-1 overflow-y-auto p-3">
        <DocumentList
          documents={documents}
          activeDocs={activeDocs}
          sessionId={sessionId}
          onActivate={handleActivate}
          onDelete={handleDelete}
        />
      </div>
    </div>
  );
}