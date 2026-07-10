// frontend/lib/api.js
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// ── Auth helpers ─────────────────────────────────────────────────

export function getToken() {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("ragverse_token");
  if (token && isTokenExpired(token)) {
    logout();
    return null;
  }
  return token;
}

export function getUser() {
  if (typeof window === "undefined") return null;
  const user = localStorage.getItem("ragverse_user");
  return user ? JSON.parse(user) : null;
}

export function logout() {
  localStorage.removeItem("ragverse_token");
  localStorage.removeItem("ragverse_user");
  window.location.href = "/";
}

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp && Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

export function scheduleTokenLogout() {
  const token = getToken();
  if (!token) return null;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const delay = payload.exp * 1000 - Date.now();
    if (delay <= 0) {
      logout();
      return null;
    }
    return window.setTimeout(logout, delay);
  } catch {
    logout();
    return null;
  }
}

function authHeaders(extra = {}) {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function handleResponse(res) {
  if (res.status === 401) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── Auth API ─────────────────────────────────────────────────────

export async function registerUser(full_name, email, password) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name, email, password }),
  });
  return handleResponse(res);
}

export async function loginUser(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

// ── Session ──────────────────────────────────────────────────────

export function getSessionId() {
  if (typeof window === "undefined") return null;
  let sessionId = localStorage.getItem("ragverse_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("ragverse_session_id", sessionId);
  }
  return sessionId;
}

export function setSessionId(sessionId) {
  if (typeof window === "undefined" || !sessionId) return;
  localStorage.setItem("ragverse_session_id", sessionId);
}

// ── Documents ────────────────────────────────────────────────────

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return handleResponse(res);
}

export async function getDocuments() {
  const res = await fetch(`${BASE_URL}/documents`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function deleteDocument(docId, sessionId) {
  const res = await fetch(`${BASE_URL}/document/${docId}?session_id=${sessionId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ── Query ────────────────────────────────────────────────────────

export async function queryDocuments(question, sessionId, docIds = null, history = [], onChunk, onSources) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      question,
      session_id: sessionId,
      doc_ids: docIds,
      history: history.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
    }),
  });

  if (response.status === 401) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  if (!response.ok) throw new Error("Query failed");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split("\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") break;

        try {
          const parsed = JSON.parse(data);
          if (parsed.type === "chunk") {
            onChunk(parsed.content);
          } else if (parsed.type === "sources") {
            onSources(parsed.sources);
          }
        } catch (e) {
          // skip malformed chunks
        }
      }
    }
  }
}

// ── Activate / Deactivate ────────────────────────────────────────

export async function activateDocument(sessionId, docId, docName) {
  const res = await fetch(`${BASE_URL}/activate`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ session_id: sessionId, doc_id: docId, doc_name: docName }),
  });
  if (!res.ok) {
    const error = await res.json();
    console.error("Activate error:", error);
    throw new Error("Activation failed");
  }
  return res.json();
}

export async function deactivateDocument(sessionId, docId) {
  const res = await fetch(`${BASE_URL}/deactivate`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ session_id: sessionId, doc_id: docId }),
  });
  return handleResponse(res);
}

export async function getActiveDocuments(sessionId) {
  const res = await fetch(`${BASE_URL}/active/${sessionId}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getChatMessages(sessionId = null) {
  const url = sessionId ? `${BASE_URL}/chat/${sessionId}` : `${BASE_URL}/chat`;
  const res = await fetch(url, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function endSession(sessionId) {
  const res = await fetch(`${BASE_URL}/session/${sessionId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function ingestUrl(url) {
  const res = await fetch(`${BASE_URL}/url`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ url }),
  });
  return handleResponse(res);
}
