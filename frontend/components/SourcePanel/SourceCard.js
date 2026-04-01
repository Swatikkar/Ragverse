"use client";
import Image from "next/image";

const FILE_ICONS = {
  pdf: "📄",
  docx: "📝",
  xlsx: "📊",
  csv: "📋",
  pptx: "📑",
  default: "📁",
};

export default function SourceCard({ source, index }) {
  const fileExt = source.doc_name?.split(".").pop() || "default";
  const icon = FILE_ICONS[fileExt] || FILE_ICONS.default;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 hover:border-gray-700 transition-all">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm shrink-0">{icon}</span>
          <p className="text-xs text-gray-300 truncate font-medium">
            {source.doc_name}
          </p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 ml-2">
          {source.from_cache && (
            <span className="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded-full">
              cached
            </span>
          )}
          {source.type === "image" && (
            <span className="text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded-full">
              image
            </span>
          )}
          <span className="text-xs text-gray-600">
            [{index}]
          </span>
        </div>
      </div>

      {/* Page / Slide info */}
      <div className="flex items-center gap-2 mb-2">
        {source.page_num && (
          <span className="text-xs text-gray-500">
            Page {source.page_num}
          </span>
        )}
        {source.score && (
          <span className="text-xs text-gray-600">
            · {Math.round(source.score * 100)}% match
          </span>
        )}
      </div>

      {/* Text preview */}
      {source.text_preview && (
        <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">
          {source.text_preview}
        </p>
      )}

      {/* Image preview */}
      {source.type === "image" && source.image_path && (
  <div className="mt-2 rounded-lg overflow-hidden border border-gray-800">
    <Image
      src={`http://localhost:8000/${source.image_path}`}
      alt="Source image"
      width={300}
      height={128}
      className="w-full object-cover max-h-32"
      onError={(e) => e.target.style.display = "none"}
    />
  </div>
)}
    </div>
  );
}