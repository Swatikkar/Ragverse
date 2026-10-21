"use client";

import { useState, useEffect } from "react";
import FileUploader from "./FileUploader";
import ActiveZone from "./ActiveZone";
import DocumentList from "./DocumentList";
import { getDocuments, getUser, logout } from "@/lib/api";
import { retryAsync } from "@/lib/retry.mjs";

export default function Sidebar({
  sessionId,
  activeDocs,
  setActiveDocs,
  activeDocsLoading,
  activeDocsError,
  onRetryActiveDocs,
}) {
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState("");
  const [documentsReload, setDocumentsReload] = useState(0);
  const user = getUser();

  useEffect(() => {
    let cancelled = false;

    async function fetchDocuments() {
      setDocumentsLoading(true);
      setDocumentsError("");
      try {
        const res = await retryAsync(() => getDocuments());
        if (!cancelled) setDocuments(res.documents || []);
      } catch (err) {
        console.error("Failed to fetch documents", err);
        if (!cancelled) setDocumentsError("Could not load your document library.");
      } finally {
        if (!cancelled) setDocumentsLoading(false);
      }
    }
    fetchDocuments();
    return () => {
      cancelled = true;
    };
  }, [documentsReload]);

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

      {/* Logo + Welcome */}
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">
          Rag<span className="text-violet-500">verse</span>
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">Multimodal Research Assistant</p>
        {user && (
          <p className="text-xs text-violet-400 mt-2">
            Welcome, {user.full_name || user.email} 👋
          </p>
        )}
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
          loading={activeDocsLoading}
          error={activeDocsError}
          onRetry={onRetryActiveDocs}
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
          loading={documentsLoading}
          error={documentsError}
          onRetry={() => setDocumentsReload((value) => value + 1)}
        />
      </div>

      {/* Logout */}
      <div className="p-3 border-t border-gray-800">
        <button
          onClick={logout}
          className="w-full text-sm text-gray-400 hover:text-red-400 hover:bg-gray-900 py-2 px-3 rounded-lg transition-colors text-left"
        >
          Sign out
        </button>
      </div>

    </div>
  );
}
