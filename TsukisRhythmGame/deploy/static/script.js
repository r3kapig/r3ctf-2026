
const questionText = document.getElementById("questionText");
const qNumLabel = document.getElementById("qNumLabel");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const answerInput = document.getElementById("answerInput");
const submitBtn = document.getElementById("submitBtn");
const feedback = document.getElementById("feedback");
const questionArea = document.getElementById("questionArea");
const finishedArea = document.getElementById("finishedArea");
const flagBox = document.getElementById("flagBox");
const specialOverlay = document.getElementById("specialOverlay");
const specialText = document.getElementById("specialText");
const specialClose = document.getElementById("specialClose");

let TOTAL = 11;

function fireConfetti() {
  const duration = 2000;
  const end = Date.now() + duration;
  (function frame() {
    confetti({
      particleCount: 6,
      angle: 60,
      spread: 80,
      origin: { x: 0 },
      colors: ['#8f7bff', '#4dc9ff', '#a675ff', '#ffffff']
    });
    confetti({
      particleCount: 6,
      angle: 120,
      spread: 80,
      origin: { x: 1 },
      colors: ['#8f7bff', '#4dc9ff', '#a675ff', '#ffffff']
    });
    if (Date.now() < end) requestAnimationFrame(frame);
  })();
  confetti({
    particleCount: 150,
    spread: 160,
    origin: { y: 0.4 }
  });
}

function updateProgress(solved, total) {
  TOTAL = total;
  const pct = (solved / total) * 100;
  progressBar.style.width = pct + "%";
  progressText.textContent = `Question ${Math.min(solved + 1, total)} / ${total}`;
}

function renderQuestion(qNum, qText, solved, total) {
  qNumLabel.textContent = "Q" + qNum;
  questionText.textContent = qText;
  updateProgress(solved, total);
  answerInput.value = "";
  feedback.textContent = "";
  feedback.className = "feedback";
}

function showFinished(flag) {
  questionArea.classList.add("hidden");
  finishedArea.classList.remove("hidden");
  flagBox.textContent = flag;
  fireConfetti();
}

function showSpecial(msg, callback) {
  specialText.textContent = msg;
  specialOverlay.classList.remove("hidden");
  specialClose.onclick = () => {
    specialOverlay.classList.add("hidden");
    if (callback) callback();
  };
}

async function loadState() {
  const res = await fetch("/api/state");
  const data = await res.json();
  if (data.finished) {
    // finished but no flag returned by state endpoint; trigger a dummy submit-less finish
    finishedArea.classList.remove("hidden");
    questionArea.classList.add("hidden");
    flagBox.textContent = "Please resubmit the last question or refresh to get the Flag";
  } else {
    renderQuestion(data.question_number, data.question_text, data.solved, data.total);
  }
}

async function submitAnswer() {
  const ans = answerInput.value.trim();
  if (!ans) {
    feedback.textContent = "Please enter your answer";
    feedback.className = "feedback wrong";
    return;
  }
  submitBtn.disabled = true;
  try {
    const res = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: ans })
    });
    const data = await res.json();

    if (data.correct) {
      fireConfetti();
      feedback.textContent = "Answer is correct!";
      feedback.className = "feedback correct";

      if (data.finished) {
        setTimeout(() => showFinished(data.flag), 800);
      } else {
        const proceed = () => {
          setTimeout(() => {
            renderQuestion(data.question_number, data.question_text, data.solved, data.total);
          }, 600);
        };
        if (data.special_message) {
          setTimeout(() => showSpecial(data.special_message, proceed), 600);
        } else {
          proceed();
        }
      }
    } else {
      feedback.textContent = data.message || "Answer is wrong";
      feedback.className = "feedback wrong";
    }
  } catch (e) {
    feedback.textContent = "Network error, please try again";
    feedback.className = "feedback wrong";
  } finally {
    submitBtn.disabled = false;
  }
}

submitBtn.addEventListener("click", submitAnswer);
answerInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitAnswer();
});

loadState();
