import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import DifficultyBar from "../components/DifficultyBar";
import EloChart from "../components/EloChart";
import SkillRadar from "../components/SkillRadar";
import { fetchDashboard } from "../lib/api";

function Dashboard() {
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        const response = await fetchDashboard(sessionId);
        setDashboard(response);
      } catch (dashboardError) {
        setError(dashboardError.message);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="app-shell">
        <div className="glass-panel p-10 text-center text-lg font-medium text-ink/70">
          Loading session dashboard...
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="app-shell">
        <div className="glass-panel p-10">
          <p className="section-title">Dashboard unavailable</p>
          <h1 className="mt-3 text-3xl font-bold">We could not load this session.</h1>
          <p className="mt-3 text-sm text-ink/70">{error || "Unknown error."}</p>
          <button className="primary-button mt-6" onClick={() => navigate("/")}>
            Start a new session
          </button>
        </div>
      </div>
    );
  }

  const topicScores =
    Object.keys(dashboard.topic_scores || {}).length > 0
      ? dashboard.topic_scores
      : { [dashboard.skill || "Overall"]: dashboard.averages?.final_score || 0 };

  return (
    <div className="app-shell space-y-6">
      <section className="glass-panel overflow-hidden">
        <div className="grid gap-6 bg-halo p-8 sm:grid-cols-2 xl:grid-cols-4">
          <div className="metric-card bg-white/80">
            <p className="section-title">Average Score</p>
            <h1 className="mt-3 text-4xl font-bold">
              {Math.round(dashboard.averages?.final_score || 0)}
            </h1>
          </div>
          <div className="metric-card bg-white/80">
            <p className="section-title">Skill Focus</p>
            <h2 className="mt-3 text-3xl font-bold">{dashboard.skill}</h2>
          </div>
          <div className="metric-card bg-white/80">
            <p className="section-title">Breakdown</p>
            <p className="mt-3 text-sm text-ink/75">
              Good {dashboard.breakdown?.Good || 0} • Average {dashboard.breakdown?.Average || 0}
              {" "}• Poor {dashboard.breakdown?.Poor || 0}
            </p>
          </div>
          <div className="metric-card bg-ink text-white">
            <p className="text-sm uppercase tracking-[0.2em] text-white/60">Recommendation</p>
            <p className="mt-3 text-sm leading-6 text-white/85">
              {dashboard.next_step || "No next-step recommendation was returned for this session."}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <EloChart values={dashboard.elo_progression || []} />
        </div>
        <SkillRadar topicScores={topicScores} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <DifficultyBar rounds={dashboard.difficulty_progression || []} />

        <div className="glass-panel overflow-hidden">
          <div className="border-b border-ink/10 px-6 py-5">
            <p className="section-title">Round Table</p>
            <h3 className="mt-2 text-2xl font-bold">Per-round scores</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0">
              <thead className="bg-ink/5 text-left text-xs uppercase tracking-[0.18em] text-ink/55">
                <tr>
                  <th className="table-cell">Round</th>
                  <th className="table-cell">Difficulty</th>
                  <th className="table-cell">Final</th>
                  <th className="table-cell">NLP</th>
                  <th className="table-cell">KG</th>
                  <th className="table-cell">Elo</th>
                  <th className="table-cell">Band</th>
                </tr>
              </thead>
              <tbody>
                {(dashboard.rounds || []).map((round) => (
                  <tr key={round.round} className="border-b border-ink/5">
                    <td className="table-cell font-semibold text-ink">{round.round}</td>
                    <td className="table-cell">{round.difficulty}</td>
                    <td className="table-cell">{round.final_score ?? "--"}</td>
                    <td className="table-cell">{round.nlp_score ?? "--"}</td>
                    <td className="table-cell">{round.kg_score ?? "--"}</td>
                    <td className="table-cell">{round.elo_after ?? "--"}</td>
                    <td className="table-cell">{round.performance_band || "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
