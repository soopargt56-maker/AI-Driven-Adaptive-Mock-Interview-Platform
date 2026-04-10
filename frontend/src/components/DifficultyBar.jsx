import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const difficultyMap = { easy: 1, medium: 2, hard: 3 };

function DifficultyBar({ rounds = [] }) {
  const data = {
    labels: rounds.map((_, index) => `R${index + 1}`),
    datasets: [
      {
        label: "Difficulty",
        data: rounds.map((value) => difficultyMap[value] || 0),
        backgroundColor: rounds.map((value) =>
          value === "hard" ? "#f26a4b" : value === "medium" ? "#d7a54d" : "#5b8a72"
        ),
        borderRadius: 12
      }
    ]
  };

  return (
    <div className="glass-panel p-6">
      <div className="mb-4">
        <p className="section-title">Adaptation</p>
        <h3 className="mt-2 text-2xl font-bold">Difficulty Progression</h3>
      </div>
      <Bar
        data={data}
        options={{
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              min: 0,
              max: 3,
              ticks: {
                stepSize: 1,
                callback(value) {
                  if (value === 1) return "Easy";
                  if (value === 2) return "Medium";
                  if (value === 3) return "Hard";
                  return "";
                }
              },
              grid: { color: "rgba(16, 33, 43, 0.08)" }
            },
            x: {
              grid: { display: false }
            }
          }
        }}
      />
    </div>
  );
}

export default DifficultyBar;
