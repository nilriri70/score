const state = {
  studentChart: null,
  teacherChart: null,
  selectedFile: null,
  lastResult: null,
};

document.addEventListener("DOMContentLoaded", () => {
  initDialogs();
  initNoticeBanner();
  initFileUpload();
  initRoundSelector();
  initGradingForm();
  loadOverview();

  document.getElementById("print-btn")?.addEventListener("click", () => window.print());
});

function initDialogs() {
  const helpDialog = document.getElementById("help-dialog");
  const videoDialog = document.getElementById("video-dialog");

  document.getElementById("open-help-btn")?.addEventListener("click", () => helpDialog?.showModal());
  document.getElementById("open-video-btn")?.addEventListener("click", () => videoDialog?.showModal());

  for (const dlg of [helpDialog, videoDialog]) {
    dlg?.addEventListener("close", () => {
      dlg.returnValue = "";
    });
  }
}

function initNoticeBanner() {
  const banner = document.getElementById("notice-banner");
  const closeBtn = document.getElementById("close-notice-btn");
  closeBtn?.addEventListener("click", () => {
    if (banner) banner.hidden = true;
  });
}

function initFileUpload() {
  const fileInput = document.getElementById("file-input");
  const fileLabel = document.getElementById("file-label");
  const dropzone = document.getElementById("upload-dropzone");

  const setFile = (file) => {
    state.selectedFile = file || null;
    if (fileLabel) {
      fileLabel.textContent = file ? `📄 ${file.name}` : "☁️ 채점할 파일 선택 (.xlsm / .xlsx)";
    }
  };

  fileInput?.addEventListener("change", (e) => {
    setFile(e.target.files?.[0]);
  });

  if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("drag-over");
    });
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
      const file = e.dataTransfer?.files?.[0];
      if (file) setFile(file);
    });
  }
}

async function initRoundSelector() {
  const select = document.getElementById("round-select");
  const downloadBtn = document.getElementById("download-round-btn");
  const statsLink = document.getElementById("statistics-link");

  try {
    const res = await fetch("/api/rounds");
    const rounds = await res.json();
    select.innerHTML = "";

    for (const r of rounds) {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = r.name;
      select.appendChild(opt);
    }

    const updateLinks = () => {
      const roundId = select.value;
      if (downloadBtn) downloadBtn.href = `/api/rounds/${encodeURIComponent(roundId)}/download`;
      updateStatisticsLink();
    };

    select.addEventListener("change", () => {
      updateLinks();
      loadOverview();
    });

    updateLinks();
  } catch (err) {
    console.error("회차 목록 로드 실패:", err);
  }

  function updateStatisticsLink() {
    if (!statsLink) return;
    const roundId = select.value || "sample_01";
    const params = new URLSearchParams({ round_id: roundId });
    if (state.lastResult) {
      params.set("my", String(state.lastResult.total_score));
      params.set("jum1", String(state.lastResult.scores.problem1));
      params.set("jum2", String(state.lastResult.scores.problem2));
      params.set("jum3", String(state.lastResult.scores.problem3));
      params.set("jum4", String(state.lastResult.scores.problem4));
    }
    statsLink.href = `/statistics?${params.toString()}`;
  }

  window.updateStatisticsLink = updateStatisticsLink;
}

function initGradingForm() {
  const form = document.getElementById("grade-form");
  const startBtn = document.getElementById("start-grade-btn");

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!state.selectedFile) {
      alert("채점할 엑셀 파일(.xlsm 또는 .xlsx)을 먼저 선택해주세요.");
      return;
    }

    const roundId = document.getElementById("round-select").value;
    const teacherId = document.getElementById("teacher-id").value;
    const studentNickname = document.getElementById("student-nickname").value;

    const formData = new FormData();
    formData.append("round_id", roundId);
    formData.append("teacher_id", teacherId);
    formData.append("student_nickname", studentNickname);
    formData.append("file", state.selectedFile);

    startBtn.disabled = true;
    startBtn.textContent = "채점 중...";

    try {
      const res = await fetch("/api/grade", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "채점에 실패했습니다.");
      }

      state.lastResult = data;
      renderGradingResult(data);
      window.updateStatisticsLink?.();
      await loadOverview();
    } catch (err) {
      alert(err.message);
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = "✅ 채점시작";
    }
  });
}

function renderGradingResult(data) {
  document.getElementById("score-p1").textContent = `${data.scores.problem1} / 20`;
  document.getElementById("score-p2").textContent = `${data.scores.problem2} / 40`;
  document.getElementById("score-p3").textContent = `${data.scores.problem3} / 20`;
  document.getElementById("score-p4").textContent = `${data.scores.problem4} / 20`;
  document.getElementById("total-score").textContent = String(data.total_score);

  const passBadge = document.getElementById("pass-badge");
  if (passBadge) {
    passBadge.hidden = false;
    passBadge.className = `badge ${data.passed ? "badge-pass" : "badge-fail"}`;
    passBadge.textContent = data.passed ? "합격 (70점 이상)" : "불합격 (70점 미만)";
  }

  const tbody = document.getElementById("deduction-tbody");
  tbody.innerHTML = "";

  if (!data.deductions.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.style.textAlign = "center";
    td.style.padding = "2rem";
    td.textContent = "🎉 감점 내역이 없습니다. 만점입니다!";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  for (const item of data.deductions) {
    const tr = document.createElement("tr");

    const tdNo = document.createElement("td");
    tdNo.textContent = item.problem_no;

    const tdTask = document.createElement("td");
    tdTask.textContent = item.task_name;

    const tdDed = document.createElement("td");
    tdDed.className = "deduction-amount";
    tdDed.textContent = String(item.deduction);

    const tdDetail = document.createElement("td");
    tdDetail.textContent = item.detail;

    tr.append(tdNo, tdTask, tdDed, tdDetail);
    tbody.appendChild(tr);
  }
}

async function loadOverview() {
  const roundId = document.getElementById("round-select")?.value;
  const query = roundId ? `?round_id=${encodeURIComponent(roundId)}` : "";

  try {
    const res = await fetch(`/api/overview${query}`);
    const data = await res.json();

    document.getElementById("participant-count").textContent = String(data.participant_count);
    document.getElementById("average-score").textContent = String(data.average_score);

    renderRankingChart("student-rank-chart", "studentChart", data.student_rankings);
    renderRankingChart("teacher-rank-chart", "teacherChart", data.teacher_rankings);
  } catch (err) {
    console.error("요약 통계 로드 실패:", err);
  }
}

function renderRankingChart(canvasId, stateKey, rows) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;

  if (state[stateKey]) {
    state[stateKey].destroy();
  }

  const labels = rows.map((r) => r.name);
  const values = rows.map((r) => r.total);
  const colors = rows.map((_, i) => {
    if (i === 0) return "#b47b38";
    if (i === 1) return "#facc15";
    if (i === 2) return "#f9a8d4";
    return "#b8bec8";
  });

  state[stateKey] = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "누적 점수",
          data: values,
          backgroundColor: colors,
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { beginAtZero: true },
      },
    },
  });
}
