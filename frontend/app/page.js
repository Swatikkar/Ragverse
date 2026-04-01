"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar/Sidebar";
import ChatWindow from "@/components/Chat/ChatWindow";
import SourcePanel from "@/components/SourcePanel/SourcePanel";

export default function Home() {
  const [activeSources, setActiveSources] = useState([]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Panel — Sidebar */}
      <div className="w-72 border-r border-gray-800 shrink-0">
        <Sidebar />
      </div>

      {/* Center Panel — Chat */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatWindow onSourcesUpdate={setActiveSources} />
      </div>

      {/* Right Panel — Sources */}
      <div className="w-80 border-l border-gray-800 shrink-0">
        <SourcePanel sources={activeSources} />
      </div>
    </div>
  );
}
