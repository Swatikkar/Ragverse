"use client";

import { useState, useRef } from "react";
import { uploadDocument } from "@/lib/api";

export default function FileUploader({ sessionId, onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const ACCEPTED_TYPES = ".pdf,.docx,.xlsx,.csv,.pptx";

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
        file_type: file.name.split(".").pop(),
        text_chunks: res.text_chunks,
        image_chunks: res.image_chunks,
      });
    } catch (err) {
      console.error(err);
      setError("Upload failed. Try again.");
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
            <p className="text-xs text-gray-600 mt-1">PDF, DOCX, XLSX, CSV, PPTX</p>
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
    </div>
  );
}