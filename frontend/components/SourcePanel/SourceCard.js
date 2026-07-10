"use client";

const FILE_ICONS = {
  pdf: "DOC",
  docx: "DOC",
  xlsx: "XLS",
  csv: "CSV",
  pptx: "PPT",
  mp3: "AUD",
  wav: "AUD",
  m4a: "AUD",
  ogg: "AUD",
  webm: "AUD",
  mp4: "AUD",
  url: "URL",
  default: "SRC",
};

export default function SourceCard({ source, index }) {
  const fileExt = source.source_type === "url" ? "url" : source.doc_name?.split(".").pop() || "default";
  const icon = FILE_ICONS[fileExt] || FILE_ICONS.default;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 hover:border-gray-700 transition-all">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] shrink-0 text-gray-500 border border-gray-700 rounded px-1 py-0.5">
            {icon}
          </span>
          <p className="text-xs text-gray-300 truncate font-medium">{source.doc_name}</p>
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
          {source.source_type && source.source_type !== "document" && (
            <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded-full">
              {source.source_type}
            </span>
          )}
          <span className="text-xs text-gray-600">[{index}]</span>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-2 min-w-0">
        {source.page_num && <span className="text-xs text-gray-500">Page {source.page_num}</span>}
        {source.language && <span className="text-xs text-gray-500">Lang {source.language}</span>}
        {source.score && <span className="text-xs text-gray-600">{Math.round(source.score * 100)}% match</span>}
      </div>

      {source.source_url && (
        <a className="block text-xs text-violet-400 truncate mb-2" href={source.source_url} target="_blank" rel="noreferrer">
          {source.source_url}
        </a>
      )}

      {source.text_preview && (
        <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">{source.text_preview}</p>
      )}

      {source.type === "image" && source.image_path && (
        <div className="mt-2 rounded-lg overflow-hidden border border-gray-800">
          <img
            src={`http://localhost:8000/${source.image_path}`}
            alt="Source"
            className="w-full object-cover max-h-32"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        </div>
      )}
    </div>
  );
}
