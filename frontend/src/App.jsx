import { Navigate, Route, Routes } from "react-router-dom";
import Upload from "./pages/Upload";
import Interview from "./pages/Interview";
import Dashboard from "./pages/Dashboard";

function App() {
  return (
    <div className="min-h-screen bg-sand text-ink">
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/interview/:sessionId" element={<Interview />} />
        <Route path="/dashboard/:sessionId" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
