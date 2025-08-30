\
(function(){
  const totalSeconds = 12 * 60; // 12 minutes
  let timeLeft = totalSeconds;
  let questions = [];
  let current = -1;
  let answers = [];

  const meaningEl = document.getElementById("meaning");
  const posInput = document.getElementById("pos-input");
  const wordInput = document.getElementById("word-input");
  const nextBtn = document.getElementById("next-btn");
  const skipBtn = document.getElementById("skip-btn");
  const timerLabel = document.getElementById("timer-label");
  const progressBar = document.getElementById("progress-bar");

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function canon(s) {
    return (s || "").trim().toLowerCase().replace(/\s+/g, " ");
  }

  function normalizePos(s) {
    const t = canon(s).replace(/\./g, "");
    const map = {
      "n": "n.", "noun": "n.",
      "v": "v.", "verb": "v.",
      "adj": "adj.", "adjective": "adj.",
      "adv": "adv.", "adverb": "adv.",
      "pron": "pron.", "pronoun": "pron.",
      "prep": "prep.", "preposition": "prep.",
      "conj": "conj.", "conjunction": "conj.",
      "interj": "interj.", "interjection": "interj."
    };
    return map[t] || (s || "").trim();
  }

  function pickNext() {
    current++;
    if (current >= questions.length) {
      // Reshuffle and continue cycling until time ends
      current = 0;
      shuffle(questions);
    }
    const q = questions[current];
    meaningEl.textContent = q.meaning;
    posInput.value = "";
    wordInput.value = "";
    wordInput.focus();
  }

  function tick() {
    timeLeft--;
    if (timeLeft < 0) {
      finish();
      return;
    }
    const m = Math.floor(timeLeft / 60);
    const s = timeLeft % 60;
    timerLabel.textContent = `Time Left: ${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    const elapsed = totalSeconds - timeLeft;
    progressBar.style.width = `${(elapsed / totalSeconds) * 100}%`;
  }

  function captureAnswer(skip=false) {
    const q = questions[current];
    const user_pos = posInput.value;
    const user_word = wordInput.value;
    const is_pos_correct = normalizePos(user_pos) === normalizePos(q.pos);
    const is_word_correct = canon(user_word) === canon(q.word);
    answers.push({
      vocab_id: q.id,
      meaning: q.meaning,
      correct_pos: q.pos,
      correct_word: q.word,
      user_pos, user_word,
      is_pos_correct, is_word_correct,
      skipped: skip
    });
  }

  async function finish() {
    clearInterval(timer);
    // send payload
    try {
      const res = await fetch("/learn/finish", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ items: answers })
      });
      const data = await res.json();
      if (data && data.redirect) {
        window.location.href = data.redirect;
      } else {
        alert("Saved, but redirect failed. Please check admin results.");
      }
    } catch (e) {
      console.error(e);
      alert("Could not save results. Please try again.");
    }
  }

  nextBtn.addEventListener("click", function(){
    captureAnswer(false);
    pickNext();
  });
  skipBtn.addEventListener("click", function(){
    captureAnswer(true);
    pickNext();
  });
  document.addEventListener("keydown", function(e){
    if (e.key === "Enter") {
      e.preventDefault();
      nextBtn.click();
    }
  });

  // Init
  fetch("/api/vocab").then(r => r.json()).then(data => {
    if (!Array.isArray(data) || data.length === 0) {
      meaningEl.textContent = "No vocabulary found. Ask Admin to add words.";
      nextBtn.disabled = true;
      skipBtn.disabled = true;
      return;
    }
    // create a working copy with randomized order
    questions = shuffle(data.slice());
    pickNext();
  });

  const timer = setInterval(tick, 1000);
  tick(); // paint initial
})();
