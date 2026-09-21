const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const predictedDigitEl = document.getElementById("predictedDigit");
const probListEl = document.getElementById("probList");
const errorMsgEl = document.getElementById("errorMsg");

const LINE_WIDTH = 18;

let drawing = false;
let hasDrawn = false;

function resetCanvas() {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = LINE_WIDTH;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  hasDrawn = false;
}

function getPos(evt) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const point = evt.touches ? evt.touches[0] : evt;
  return {
    x: (point.clientX - rect.left) * scaleX,
    y: (point.clientY - rect.top) * scaleY,
  };
}

function startDraw(evt) {
  evt.preventDefault();
  drawing = true;
  hasDrawn = true;
  const { x, y } = getPos(evt);
  ctx.beginPath();
  ctx.moveTo(x, y);
}

function draw(evt) {
  if (!drawing) return;
  evt.preventDefault();
  const { x, y } = getPos(evt);
  ctx.lineTo(x, y);
  ctx.stroke();
}

function stopDraw(evt) {
  if (!drawing) return;
  evt.preventDefault();
  drawing = false;
}

canvas.addEventListener("mousedown", startDraw);
canvas.addEventListener("mousemove", draw);
canvas.addEventListener("mouseup", stopDraw);
canvas.addEventListener("mouseleave", stopDraw);

canvas.addEventListener("touchstart", startDraw);
canvas.addEventListener("touchmove", draw);
canvas.addEventListener("touchend", stopDraw);

document.getElementById("clearBtn").addEventListener("click", () => {
  resetCanvas();
  predictedDigitEl.textContent = "?";
  probListEl.innerHTML = "";
  errorMsgEl.textContent = "";
});

document.getElementById("predictBtn").addEventListener("click", async () => {
  errorMsgEl.textContent = "";

  if (!hasDrawn) {
    errorMsgEl.textContent = "캔버스에 숫자를 먼저 그려주세요.";
    return;
  }

  const dataUrl = canvas.toDataURL("image/png");

  try {
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataUrl }),
    });
    const result = await res.json();

    if (!res.ok) {
      errorMsgEl.textContent = result.error || "예측 중 오류가 발생했습니다.";
      return;
    }

    renderResult(result);
  } catch (err) {
    errorMsgEl.textContent = "서버에 연결할 수 없습니다.";
  }
});

function renderResult({ prediction, probabilities }) {
  predictedDigitEl.textContent = prediction;

  probListEl.innerHTML = "";
  probabilities.forEach((p, digit) => {
    const row = document.createElement("div");
    row.className = "prob-row" + (digit === prediction ? " top" : "");

    const label = document.createElement("span");
    label.textContent = digit;

    const track = document.createElement("div");
    track.className = "prob-bar-track";
    const fill = document.createElement("div");
    fill.className = "prob-bar-fill";
    fill.style.width = `${Math.round(p * 100)}%`;
    track.appendChild(fill);

    const pct = document.createElement("span");
    pct.textContent = `${Math.round(p * 100)}%`;

    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(pct);
    probListEl.appendChild(row);
  });
}

resetCanvas();
