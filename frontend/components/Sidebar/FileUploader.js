"use client";

import { useState, useRef } from "react";
import { ingestUrl, uploadDocument } from "@/lib/api";

export default function FileUploader({ sessionId, onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [urlLoading, setUrlLoading] = useState(false);
  const [url, setUrl] = useState("");
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const ACCEPTED_TYPES = ".pdf,.docx,.xlsx,.csv,.pptx,.mp3,.wav,.m4a,.ogg,.webm,.mp4";

  async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    await handleUpload(file);
  }

  async function handleUpload(file) {
    setUploading(true);
    setError(null);

    try {
      const res = await uploadDocument(file);
      onUploaded({
        doc_id: res.doc_id,
        doc_name: res.doc_name,
        file_type: res.file_type || file.name.split(".").pop(),
        source_type: res.source_type || "document",
        text_chunks: res.text_chunks,
        image_chunks: res.image_chunks,
      });
    } catch (err) {
      console.error(err);
      setError(err.message || "Upload failed. Try again.");
    } finally {
      setUploading(false);
      inputRef.current.value = "";
    }
  }

  async function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    await handleUpload(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  async function handleUrlSubmit(e) {
    e.preventDefault();
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;

    try {
      const parsedUrl = new URL(trimmedUrl);
      if (!["http:", "https:"].includes(parsedUrl.protocol)) {
        setError("Enter a valid http(s) URL.");
        return;
      }
    } catch {
      setError("Enter a valid http(s) URL.");
      return;
    }

    setUrlLoading(true);
    setError(null);

    try {
      const res = await ingestUrl(trimmedUrl);
      onUploaded({
        doc_id: res.doc_id,
        doc_name: res.doc_name,
        file_type: res.file_type,
        source_type: res.source_type,
        source_url: res.source_url,
        text_chunks: res.text_chunks,
        image_chunks: res.image_chunks,
      });
      setUrl("");
    } catch (err) {
      console.error(err);
      setError(err.message || "URL ingestion failed.");
    } finally {
      setUrlLoading(false);
    }
  }

  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Upload
      </p>

      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => inputRef.current.click()}
        className="border border-dashed border-gray-700 rounded-lg p-4 text-center cursor-pointer hover:border-violet-500 hover:bg-violet-500/5 transition-all"
      >
        {uploading ? (
          <p className="text-xs text-violet-400 animate-pulse">Processing...</p>
        ) : (
          <>
            <p className="text-xs text-gray-400">Drop file or click to upload</p>
            <p className="text-xs text-gray-600 mt-1">PDF, DOCX, XLSX, CSV, PPTX, audio</p>
          </>
        )}
      </div>

      {/* Hidden Input */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Error */}
      {error && (
        <p className="text-xs text-red-400 mt-2">{error}</p>
      )}

      <form onSubmit={handleUrlSubmit} className="mt-3 flex gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          type="text"
          placeholder="https://example.com/article"
          className="min-w-0 flex-1 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
        />
        <button
          type="submit"
          disabled={urlLoading || !url.trim()}
          className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs text-gray-200"
        >
          {urlLoading ? "..." : "Add"}
        </button>
      </form>
    </div>
  );
}
