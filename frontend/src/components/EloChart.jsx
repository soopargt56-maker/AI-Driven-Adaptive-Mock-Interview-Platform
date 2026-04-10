import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

function EloChart({ values = [] }) {
  const data = {
    labels: values.map((_, index) => `R${index + 1}`),
    datasets: [
      {
        label: "Elo",
        data: values,
        borderColor: "#246a73",
        backgroundColor: "rgba(36, 106, 115, 0.18)",
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#f26a4b"
      }
    ]
  };

  return (
    <div className="glass-panel p-6">
      <div className="mb-4">
        <p className="section-title">Performance Momentum</p>
        <h3 className="mt-2 text-2xl font-bold">Elo Trajectory</h3>
      </div>
      <Line
        data={data}
        options={{
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: {
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

export default EloChart;
