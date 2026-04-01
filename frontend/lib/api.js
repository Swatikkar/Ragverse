const BASE_URL = "http://localhost:8000/api";

// Upload a document
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

// Get all documents
export async function getDocuments() {
  const res = await fetch(`${BASE_URL}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

// Delete a document
export async function deleteDocument(docId, sessionId) {
  const res = await fetch(`${BASE_URL}/document/${docId}?session_id=${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

// Query documents
export async function queryDocuments(question, sessionId, docIds = null, history = []) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      doc_ids: docIds,
      history: history.map(msg => ({
        role: msg.role,
        content: msg.content
      }))
    }),
  });
  if (!res.ok) throw new Error("Query failed");
  return res.json();
}

// Activate a document
// export async function activateDocument(sessionId, docId, docName) {
//   const res = await fetch(`${BASE_URL}/activate`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({
//       session_id: sessionId,
//       doc_id: docId,
//       doc_name: docName,
//     }),
//   });
//   if (!res.ok) throw new Error("Activation failed");
//   return res.json();
// }
export async function activateDocument(sessionId, docId, docName) {
  const res = await fetch(`${BASE_URL}/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      doc_id: docId,
      doc_name: docName,
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    console.error("Activate error:", error);  // add this
    throw new Error("Activation failed");
  }
  return res.json();
}

// Deactivate a document
export async function deactivateDocument(sessionId, docId) {
  const res = await fetch(`${BASE_URL}/deactivate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      doc_id: docId,
    }),
  });
  if (!res.ok) throw new Error("Deactivation failed");
  return res.json();
}

// Get active documents
export async function getActiveDocuments(sessionId) {
  const res = await fetch(`${BASE_URL}/active/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch active documents");
  return res.json();
}

// End session
export async function endSession(sessionId) {
  const res = await fetch(`${BASE_URL}/session/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to end session");
  return res.json();
}

export function getSessionId() {
  if (typeof window === "undefined") return null;
  
  let sessionId = localStorage.getItem("ragverse_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("ragverse_session_id", sessionId);
  }
  return sessionId;
}