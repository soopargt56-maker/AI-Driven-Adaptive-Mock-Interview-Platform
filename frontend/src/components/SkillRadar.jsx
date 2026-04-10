import {
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  PointElement,
  RadialLinearScale,
  Tooltip
} from "chart.js";
import { Radar } from "react-chartjs-2";

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

function SkillRadar({ topicScores = {} }) {
  const labels = Object.keys(topicScores);
  const values = Object.values(topicScores);

  return (
    <div className="glass-panel p-6">
      <div className="mb-4">
        <p className="section-title">Knowledge Coverage</p>
        <h3 className="mt-2 text-2xl font-bold">Topic Radar</h3>
      </div>
      <div className="relative aspect-square w-full">
      <Radar
        data={{
          labels,
          datasets: [
            {
              label: "Average topic score",
              data: values,
              backgroundColor: "rgba(242, 106, 75, 0.18)",
              borderColor: "#f26a4b",
              pointBackgroundColor: "#246a73"
            }
          ]
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            r: {
              min: 0,
              max: 100,
              ticks: { backdropColor: "transparent" },
              grid: { color: "rgba(16, 33, 43, 0.10)" },
              angleLines: { color: "rgba(16, 33, 43, 0.10)" }
            }
          }
        }}
      />
      </div>
    </div>
  );
}

export default SkillRadar;
