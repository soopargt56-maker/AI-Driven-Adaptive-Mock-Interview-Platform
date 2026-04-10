const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const SESSION_STORAGE_KEY = "adaptive-mock-interview-state";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }

  return data;
}

export function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/resume", { method: "POST", body: formData });
}

export function startSession(payload) {
  return request("/session/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function submitAnswer(payload) {
  return request("/session/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function fetchDashboard(sessionId) {
  return request(`/dashboard/${sessionId}`);
}

function tokenize(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

export function buildAnswerMetrics(question, answer) {
  const questionTokens = tokenize(question);
  const answerTokens = tokenize(answer);
  const uniqueQuestion = new Set(questionTokens);
  const uniqueAnswer = new Set(answerTokens);
  const overlap = [...uniqueAnswer].filter((token) => uniqueQuestion.has(token)).length;
  const wordCount = answerTokens.length;
  const overlapRatio = uniqueQuestion.size ? overlap / uniqueQuestion.size : 0;

  return {
    cos_similarity: Number(overlapRatio.toFixed(2)),
    length_ratio: Number(Math.min(wordCount / 60, 1.5).toFixed(2)),
    aligned_score: Number((overlapRatio * 100).toFixed(2)),
    word_count: wordCount
  };
}

export function saveInterviewState(state) {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(state));
}

export function loadInterviewState() {
  const raw = localStorage.getItem(SESSION_STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function clearInterviewState() {
  localStorage.removeItem(SESSION_STORAGE_KEY);
}
