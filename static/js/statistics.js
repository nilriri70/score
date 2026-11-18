const CHART_COLORS = [
  "#1D2B9C",
  "#5A92C9",
  "#B951F0",
  "#EDE765",
  "#879ECF",
  "#3949AB",
  "#7986CB",
  "#AB47BC",
  "#4FC3F7",
  "#FFD54F",
  "#283593",
];

const chartInstances = {};

document.addEventListener("DOMContentLoaded", async () => {
  const params = new URLSearchParams(window.location.search);
  const initialRound = params.get("round_id") || "sample_01";
  const myScores = {
    total: parseOptionalInt(params.get("my")),
    p1: parseOptionalInt(params.get("jum1")),
    p2: parseOptionalInt(params.get("jum2")),
    p3: parseOptionalInt(params.get("jum3")),
    p4: parseOptionalInt(params.get("jum4")),
  };

  await initRoundSelect(initialRound, myScores);
  await loadStatistics(initialRound, myScores);
});

function parseOptionalInt(val) {
  if (val === null || val === "") return null;
  const num = Number(val);
  return Number.isFinite(num) ? num : null;
}

async function initRoundSelect(initialRound, myScores) {
  const select = document.getElementById("stats-round-select");
  const res = await fetch("/api/rounds");
  const rounds = await res.json();

  select.innerHTML = "";
  for (const r of rounds) {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = r.name;
    if (r.id === initialRound) opt.selected = true;
    select.appendChild(opt);
  }

  select.addEventListener("change", () => {
    loadStatistics(select.value, myScores);
  });
}

async function loadStatistics(roundId, myScores) {
  const res = await fetch(`/api/statistics?round_id=${encodeURIComponent(roundId)}`);
  const data = await res.json();

  document.getElementById("stats-total-count").textContent = `총 ${data.count}명`;

  renderDistributionPie("chart-total", data.total, myScores.total);
  renderDistributionPie("chart-p1", data.problem1, myScores.p1);
  renderDistributionPie("chart-p2", data.problem2, myScores.p2);
  renderDistributionPie("chart-p3", data.problem3, myScores.p3);
  renderDistributionPie("chart-p4", data.problem4, myScores.p4);
}

function isScoreInBucket(score, bucket) {
  if (score === null) return false;
  return bucket.inc_high
    ? score >= bucket.low && score <= bucket.high
    : score >= bucket.low && score < bucket.high;
}

function renderDistributionPie(canvasId, buckets, myScore) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;

  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }

  const labels = buckets.map((b) =>
    isScoreInBucket(myScore, b) ? `${b.label} [내 점수]` : b.label
  );
  const counts = buckets.map((b) => b.count);
  const offsets = buckets.map((b) => (isScoreInBucket(myScore, b) ? 16 : 0));

  chartInstances[canvasId] = new Chart(canvas, {
    type: "pie",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          backgroundColor: CHART_COLORS.slice(0, buckets.length),
          offset: offsets,
          borderWidth: 1,
          borderColor: "#ffffff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: {
            boxWidth: 12,
            font: { size: 12 },
          },
        },
      },
    },
  });
}
