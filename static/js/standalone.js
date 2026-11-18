/* global Chart, XLSX */
let HAS_SERVER = false;
const STORAGE_KEY = "comlicense_score_submissions_v1";

const DEFAULT_ROUNDS = [
  { id: "sample_01", name: "대표기출따라하기", file: "data/problems/sample_01.xlsm" },
  { id: "mock_01", name: "모의고사 1회 (예시)", file: "data/problems/sample_01.xlsm" },
];

const SEED_SUBMISSIONS = [
  { round_id: "sample_01", teacher_id: "t_kim01", student_nickname: "오*진", p1: 20, p2: 32, p3: 20, p4: 18, total: 90 },
  { round_id: "sample_01", teacher_id: "t_kim01", student_nickname: "봉*수", p1: 18, p2: 40, p3: 10, p4: 16, total: 84 },
  { round_id: "sample_01", teacher_id: "t_park2", student_nickname: "송*라", p1: 15, p2: 24, p3: 20, p4: 15, total: 74 },
  { round_id: "sample_01", teacher_id: "t_park2", student_nickname: "김*민", p1: 10, p2: 16, p3: 10, p4: 10, total: 46 },
  { round_id: "sample_01", teacher_id: "t_lee03", student_nickname: "이*현", p1: 20, p2: 40, p3: 20, p4: 20, total: 100 },
  { round_id: "sample_01", teacher_id: "t_lee03", student_nickname: "박*우", p1: 5, p2: 8, p3: 0, p4: 4, total: 17 },
  { round_id: "sample_01", teacher_id: "t_choi4", student_nickname: "정*서", p1: 12, p2: 16, p3: 10, p4: 12, total: 50 },
  { round_id: "sample_01", teacher_id: "t_kim01", student_nickname: "최*아", p1: 0, p2: 0, p3: 0, p4: 5, total: 5 },
  { round_id: "sample_01", teacher_id: "t_park2", student_nickname: "강*준", p1: 2, p2: 0, p3: 0, p4: 2, total: 4 },
  { round_id: "sample_01", teacher_id: "t_jung5", student_nickname: "윤*호", p1: 15, p2: 24, p3: 10, p4: 14, total: 63 },
];

const PIE_COLORS = [
  "#2f66d0", "#dc3912", "#ff9900", "#109618", "#990099",
  "#0099c6", "#dd4477", "#66aa00", "#b82e2e", "#316395", "#8e24aa",
];

const state = {
  studentChart: null,
  teacherChart: null,
  pieCharts: {},
  selectedFile: null,
  lastResult: null,
};

document.addEventListener("DOMContentLoaded", async () => {
  HAS_SERVER = await detectFastApiServer();
  initLocalStore();
  initDialogs();
  initNoticeBanner();
  initFileUpload();
  await initRoundSelector();
  initGradingForm();
  await loadOverview();

  document.getElementById("print-btn")?.addEventListener("click", () => window.print());
});

async function detectFastApiServer() {
  if (!window.location.protocol.startsWith("http")) return false;
  try {
    const res = await fetch("/api/rounds", { headers: { Accept: "application/json" } });
    const ct = res.headers.get("content-type") || "";
    return res.ok && ct.includes("application/json");
  } catch {
    return false;
  }
}

function initLocalStore() {
  if (HAS_SERVER) return;
  if (!localStorage.getItem(STORAGE_KEY)) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(SEED_SUBMISSIONS));
  }
}

function getLocalSubmissions() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [...SEED_SUBMISSIONS];
  }
}

function initDialogs() {
  const helpDialog = document.getElementById("help-dialog");
  const videoDialog = document.getElementById("video-dialog");
  const statsDialog = document.getElementById("stats-dialog");

  document.getElementById("open-help-btn")?.addEventListener("click", () => helpDialog?.showModal());
  document.getElementById("open-video-btn")?.addEventListener("click", () => videoDialog?.showModal());

  document.getElementById("statistics-link")?.addEventListener("click", (e) => {
    if (!HAS_SERVER) {
      e.preventDefault();
      openLocalStatisticsDialog();
      statsDialog?.showModal();
    }
  });

  for (const dlg of [helpDialog, videoDialog, statsDialog]) {
    dlg?.addEventListener("close", () => {
      dlg.returnValue = "";
    });
  }
}

function initNoticeBanner() {
  const banner = document.getElementById("notice-banner");
  document.getElementById("close-notice-btn")?.addEventListener("click", () => {
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

  fileInput?.addEventListener("change", (e) => setFile(e.target.files?.[0]));

  if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
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

  let rounds = DEFAULT_ROUNDS;
  if (HAS_SERVER) {
    try {
      const res = await fetch("/api/rounds");
      rounds = await res.json();
    } catch (err) {
      console.error("회차 목록 로드 실패:", err);
    }
  }

  select.innerHTML = "";
  for (const r of rounds) {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = r.name;
    select.appendChild(opt);
  }

  const updateLinks = () => {
    const roundId = select.value || "sample_01";
    if (downloadBtn) {
      downloadBtn.href = HAS_SERVER
        ? `/api/rounds/${encodeURIComponent(roundId)}/download`
        : "data/problems/sample_01.xlsm";
    }
    updateStatisticsLink();
  };

  select.addEventListener("change", () => {
    updateLinks();
    loadOverview();
  });

  updateLinks();
}

function updateStatisticsLink() {
  const statsLink = document.getElementById("statistics-link");
  const select = document.getElementById("round-select");
  if (!statsLink || !select) return;

  const roundId = select.value || "sample_01";
  const params = new URLSearchParams({ round_id: roundId });
  if (state.lastResult) {
    params.set("my", String(state.lastResult.total_score));
    params.set("jum1", String(state.lastResult.scores.problem1));
    params.set("jum2", String(state.lastResult.scores.problem2));
    params.set("jum3", String(state.lastResult.scores.problem3));
    params.set("jum4", String(state.lastResult.scores.problem4));
  }
  statsLink.href = HAS_SERVER ? `/statistics?${params.toString()}` : "#statistics";
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
    const teacherId = document.getElementById("teacher-id").value.trim() || "미입력";
    const studentNickname = document.getElementById("student-nickname").value.trim() || "익명학생";

    startBtn.disabled = true;
    startBtn.textContent = "채점 중...";

    try {
      let result;
      if (HAS_SERVER) {
        const formData = new FormData();
        formData.append("round_id", roundId);
        formData.append("teacher_id", teacherId);
        formData.append("student_nickname", studentNickname);
        formData.append("file", state.selectedFile);

        const res = await fetch("/api/grade", { method: "POST", body: formData });
        result = await res.json();
        if (!res.ok) throw new Error(result.detail || "채점에 실패했습니다.");
      } else {
        result = await gradeLocallyInBrowser(state.selectedFile, roundId, teacherId, studentNickname);
      }

      state.lastResult = result;
      renderGradingResult(result);
      updateStatisticsLink();
      await loadOverview();
    } catch (err) {
      alert(err.message || "파일 분석 중 오류가 발생했습니다.");
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = "✅ 채점시작";
    }
  });
}

async function gradeLocallyInBrowser(file, roundId, teacherId, studentNickname) {
  if (typeof XLSX === "undefined") {
    throw new Error("오프라인 상태에서는 엑셀 파서(SheetJS)를 불러올 수 없습니다.");
  }

  const buffer = await file.arrayBuffer();
  const wb = XLSX.read(buffer, { type: "array" });
  const names = new Set(wb.SheetNames);
  const deductions = [];

  // 문제1: 기본작업 (20점)
  let p1 = 0;
  if (names.has("기본작업-1")) p1 += 5;
  else deductions.push({ problem_no: "문제1-1", task_name: "기본작업-1 (데이터 입력)", deduction: -5, detail: "'기본작업-1' 시트 누락" });

  if (names.has("기본작업-2")) p1 += 10;
  else deductions.push({ problem_no: "문제1-2", task_name: "기본작업-2 (셀 서식)", deduction: -10, detail: "'기본작업-2' 시트 누락" });

  if (names.has("기본작업-3")) p1 += 5;
  else deductions.push({ problem_no: "문제1-3", task_name: "기본작업-3 (고급필터/조건부서식)", deduction: -5, detail: "'기본작업-3' 시트 누락" });

  // 문제2: 계산작업 (40점 — 5문항 × 8점, 부분점수 없음)
  let p2 = 0;
  const calcWs = wb.Sheets["계산작업"];
  const calcCells = [
    { cell: "D3", title: "계산작업 1번 ([표1] 도착시간)" },
    { cell: "I3", title: "계산작업 2번 ([표2] 부서별 실적)" },
    { cell: "D24", title: "계산작업 3번 ([표3] 드라마 예매량 평균)" },
    { cell: "J14", title: "계산작업 4번 ([표4] 당첨층)" },
    { cell: "E28", title: "계산작업 5번 ([표5] 수강과목)" },
  ];
  if (!calcWs) {
    deductions.push({ problem_no: "문제2", task_name: "계산작업", deduction: -40, detail: "'계산작업' 시트 누락" });
  } else {
    calcCells.forEach((q, idx) => {
      const cellObj = calcWs[q.cell];
      if (cellObj && cellObj.f) {
        p2 += 8;
      } else {
        deductions.push({
          problem_no: `문제2-${idx + 1}`,
          task_name: q.title,
          deduction: -8,
          detail: `${q.cell} 셀에 수식(=)이 입력되지 않았습니다.`,
        });
      }
    });
  }

  // 문제3: 분석작업 (20점)
  let p3 = 0;
  if (names.has("분석작업-1")) p3 += 10;
  else deductions.push({ problem_no: "문제3-1", task_name: "분석작업-1", deduction: -10, detail: "'분석작업-1' 시트 누락" });

  if (names.has("분석작업-2")) p3 += 10;
  else deductions.push({ problem_no: "문제3-2", task_name: "분석작업-2", deduction: -10, detail: "'분석작업-2' 시트 누락" });

  // 문제4: 기타작업 (20점)
  let p4 = 0;
  if (names.has("매크로작업")) p4 += 10;
  else deductions.push({ problem_no: "문제4-1", task_name: "매크로작업", deduction: -10, detail: "'매크로작업' 시트 누락" });

  if (names.has("차트작업")) p4 += 10;
  else deductions.push({ problem_no: "문제4-2", task_name: "차트작업", deduction: -10, detail: "'차트작업' 시트 누락" });

  const total = p1 + p2 + p3 + p4;
  const rows = getLocalSubmissions();
  rows.push({ round_id: roundId, teacher_id: teacherId, student_nickname: studentNickname, p1, p2, p3, p4, total });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));

  return {
    round_id: roundId,
    scores: { problem1: p1, problem2: p2, problem3: p3, problem4: p4 },
    total_score: total,
    passed: total >= 70,
    deductions,
  };
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
  const roundId = document.getElementById("round-select")?.value || "sample_01";

  if (HAS_SERVER) {
    try {
      const res = await fetch(`/api/overview?round_id=${encodeURIComponent(roundId)}`);
      const data = await res.json();
      document.getElementById("participant-count").textContent = String(data.participant_count);
      document.getElementById("average-score").textContent = String(data.average_score);
      renderRankingChart("student-rank-chart", "studentChart", data.student_rankings);
      renderRankingChart("teacher-rank-chart", "teacherChart", data.teacher_rankings);
    } catch (err) {
      console.error("요약 통계 로드 실패:", err);
    }
    return;
  }

  const rows = getLocalSubmissions().filter((r) => r.round_id === roundId);
  const cnt = rows.length;
  const avg = cnt ? (rows.reduce((acc, r) => acc + r.total, 0) / cnt).toFixed(2) : "0";
  document.getElementById("participant-count").textContent = String(cnt);
  document.getElementById("average-score").textContent = avg;

  const allRows = getLocalSubmissions();
  const studentMap = new Map();
  const teacherMap = new Map();
  for (const r of allRows) {
    if (r.student_nickname && r.student_nickname !== "익명학생") {
      studentMap.set(r.student_nickname, (studentMap.get(r.student_nickname) || 0) + r.total);
    }
    if (r.teacher_id && r.teacher_id !== "미입력") {
      teacherMap.set(r.teacher_id, (teacherMap.get(r.teacher_id) || 0) + r.total);
    }
  }

  const studentRanks = [...studentMap.entries()].map(([name, total]) => ({ name, total })).sort((a, b) => b.total - a.total).slice(0, 10);
  const teacherRanks = [...teacherMap.entries()].map(([name, total]) => ({ name, total })).sort((a, b) => b.total - a.total).slice(0, 5);

  renderRankingChart("student-rank-chart", "studentChart", studentRanks);
  renderRankingChart("teacher-rank-chart", "teacherChart", teacherRanks);
}

function renderRankingChart(canvasId, stateKey, rows) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;
  if (state[stateKey]) state[stateKey].destroy();

  const colors = rows.map((_, i) => (i === 0 ? "#b47b38" : i === 1 ? "#facc15" : i === 2 ? "#f9a8d4" : "#b8bec8"));

  state[stateKey] = new Chart(canvas, {
    type: "bar",
    data: {
      labels: rows.map((r) => r.name),
      datasets: [{ label: "누적 점수", data: rows.map((r) => r.total), backgroundColor: colors, borderRadius: 4 }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true } },
    },
  });
}

function openLocalStatisticsDialog() {
  const roundId = document.getElementById("round-select")?.value || "sample_01";
  const rows = getLocalSubmissions().filter((r) => r.round_id === roundId);
  const my = state.lastResult;

  const bucket = (values, bins) =>
    bins.map(([label, low, high, inc]) => ({
      label,
      low,
      high,
      inc,
      count: values.filter((v) => (inc ? v >= low && v <= high : v >= low && v < high)).length,
    }));

  const totalBins = Array.from({ length: 10 }, (_, i) => [`${i * 10}~${(i + 1) * 10}점미만`, i * 10, (i + 1) * 10, false]);
  totalBins.push(["100", 100, 100, true]);

  const bins20 = [
    ["0~5점미만", 0, 5, false], ["5~10점미만", 5, 10, false],
    ["10~15점미만", 10, 15, false], ["15~20점미만", 15, 20, false], ["20", 20, 20, true],
  ];
  const bins40 = Array.from({ length: 8 }, (_, i) => [`${i * 5}~${(i + 1) * 5}점미만`, i * 5, (i + 1) * 5, false]);
  bins40.push(["40", 40, 40, true]);

  renderModalPie("modal-chart-total", bucket(rows.map((r) => r.total), totalBins), my?.total_score ?? null);
  renderModalPie("modal-chart-p1", bucket(rows.map((r) => r.p1), bins20), my?.scores.problem1 ?? null);
  renderModalPie("modal-chart-p2", bucket(rows.map((r) => r.p2), bins40), my?.scores.problem2 ?? null);
  renderModalPie("modal-chart-p3", bucket(rows.map((r) => r.p3), bins20), my?.scores.problem3 ?? null);
  renderModalPie("modal-chart-p4", bucket(rows.map((r) => r.p4), bins20), my?.scores.problem4 ?? null);
}

function renderModalPie(canvasId, buckets, myScore) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;
  if (state.pieCharts[canvasId]) state.pieCharts[canvasId].destroy();

  const inBucket = (b) => myScore !== null && (b.inc ? myScore >= b.low && myScore <= b.high : myScore >= b.low && myScore < b.high);

  state.pieCharts[canvasId] = new Chart(canvas, {
    type: "pie",
    data: {
      labels: buckets.map((b) => (inBucket(b) ? `${b.label} [내 점수]` : b.label)),
      datasets: [{
        data: buckets.map((b) => b.count),
        backgroundColor: PIE_COLORS.slice(0, buckets.length),
        offset: buckets.map((b) => (inBucket(b) ? 14 : 0)),
        borderColor: "#ffffff",
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "right", labels: { boxWidth: 10, font: { size: 11 } } } },
    },
  });
}
