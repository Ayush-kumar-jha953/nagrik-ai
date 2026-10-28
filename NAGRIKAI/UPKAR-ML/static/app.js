const box = document.getElementById("message");
const count = document.getElementById("count");
const button = document.getElementById("check");
const result = document.getElementById("result");
const verdict = document.getElementById("verdict");
const meter = document.getElementById("meter");
const meterWrap = document.getElementById("meter-wrap");
const detail = document.getElementById("detail");
const maxChars = box.maxLength;

function show(kind, title, pct, text) {
  result.hidden = false;
  result.className = "result " + kind;
  verdict.textContent = title;
  meterWrap.hidden = pct === null;
  meter.style.width = (pct || 0) + "%";
  detail.textContent = text;
}

box.addEventListener("input", () => {
  count.textContent = `${box.value.length} / ${maxChars}`;
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    box.value = chip.dataset.text;
    box.dispatchEvent(new Event("input"));
    box.focus();
  });
});

button.addEventListener("click", async () => {
  const message = box.value.trim();
  if (!message) {
    show("error", "Nothing to check", null, "Enter a message above, then select Check message.");
    return;
  }

  button.disabled = true;
  button.textContent = "Checking…";
  try {
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok) {
      show("error", "Could not check this message", null, data.error || "Please try again.");
      return;
    }

    if (data.label === "unclear") {
      show("", "Not enough text to judge", null,
        "The message has too few meaningful words. Add more detail and check again.");
    } else {
      const pct = Math.round(data.confidence * 100);
      const good = data.label === "good";
      show(good ? "good" : "bad",
           good ? "Acceptable" : "Flagged for review",
           pct,
           `Model signal: about ${pct}%. This is a rough indicator, not a probability. Use it to support a human decision, not replace it.`);
    }
  } catch (err) {
    show("error", "Server unreachable", null, "Check that the Flask app is running, then try again.");
  } finally {
    button.disabled = false;
    button.textContent = "Check message";
  }
});
