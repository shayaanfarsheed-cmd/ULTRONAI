(function () {
  "use strict";
  function init() {
    const agent = window.ULTRON_MATH_AGENT;
    const tutorApi = window.ULTRON_MATH_TUTOR;
    const reasoning = window.ULTRON_REASONING;
    const root = document.getElementById("mathTutorPanel");
    if (!agent || !tutorApi || !root) return;
    const tutor = tutorApi.createTutor(agent, reasoning);
    const questionNode = document.getElementById("tutorQuestion");
    const answerNode = document.getElementById("tutorAnswer");
    const feedback = document.getElementById("tutorFeedback");
    const hintNode = document.getElementById("tutorHint");
    const masteryNode = document.getElementById("tutorMastery");
    const topicNode = document.getElementById("tutorTopic");
    let exercise = null;
    let hints = [];
    let hintIndex = 0;
    let answered = false;

    function text(parent, tag, className, value) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      node.textContent = value;
      parent.appendChild(node);
      return node;
    }
    function renderMastery() {
      masteryNode.replaceChildren();
      const snapshot = tutor.getSnapshot();
      const due = new Set(snapshot.dueTopics);
      snapshot.topics.forEach(item => {
        const row = document.createElement("div");
        row.className = "tutor-mastery-row";
        const title = text(row, "span", "tutor-mastery-name", agent.TOPICS[item.topic].label);
        title.title = item.topic;
        const bar = document.createElement("span");
        bar.className = "tutor-mastery-track";
        const fill = document.createElement("span");
        fill.className = "tutor-mastery-fill";
        fill.style.width = Math.round(item.accuracy * 100) + "%";
        bar.appendChild(fill);
        row.appendChild(bar);
        text(row, "strong", "tutor-mastery-value", item.attempts ? Math.round(item.accuracy * 100) + "%" : "NEW");
        if (due.has(item.topic)) text(row, "small", "tutor-due-label", "REVIEW DUE");
        masteryNode.appendChild(row);
      });
      document.getElementById("tutorSessionStatus").textContent =
        "Session turn " + snapshot.turn + " · " + snapshot.dueTopics.length + " reviews due · memory only";
    }
    function next() {
      try {
        exercise = tutor.nextExercise();
        hints = tutor.getHints(exercise.topic, exercise.question).hints;
        hintIndex = 0;
        answered = false;
        topicNode.textContent = agent.TOPICS[exercise.topic].label + " · fixed foundation difficulty";
        questionNode.textContent = exercise.question;
        answerNode.value = "";
        feedback.textContent = "Try the question. Your answer is checked independently.";
        hintNode.textContent = "Hints are available one step at a time.";
        renderMastery();
      } catch (error) {
        feedback.textContent = error.message || "Could not create a verified exercise.";
      }
    }
    document.getElementById("tutorNextButton").addEventListener("click", next);
    document.getElementById("tutorHintButton").addEventListener("click", () => {
      if (!exercise || hintIndex >= hints.length) {
        hintNode.textContent = hints.length ? "You have seen all three hints." : "Generate a question first.";
        return;
      }
      const hint = hints[hintIndex++];
      hintNode.textContent = "HINT " + hint.level + " · " + hint.title + ": " + hint.text;
    });
    document.getElementById("tutorAnswerForm").addEventListener("submit", event => {
      event.preventDefault();
      if (!exercise) {
        feedback.textContent = "Generate a question first.";
        return;
      }
      if (answered) { feedback.textContent = "This question has already been recorded. Generate a new question to continue."; return; }
      const diagnosis = tutor.diagnose(exercise.topic, exercise.question, answerNode.value);
      if (diagnosis.status !== "correct" && diagnosis.status !== "incorrect_unclassified") {
        feedback.textContent = diagnosis.message;
        return;
      }
      tutor.recordAttempt(exercise.topic, diagnosis.status === "correct");
      answered = true;
      feedback.textContent = diagnosis.status === "correct"
        ? diagnosis.message
        : diagnosis.message + " Verified answer: " + diagnosis.expected + ".";
      renderMastery();
    });
    document.getElementById("tutorResetButton").addEventListener("click", () => {
      tutor.reset();
      exercise = null;
      hints = [];
      hintIndex = 0;
      topicNode.textContent = "No active question";
      questionNode.textContent = "Choose New question to begin.";
      answerNode.value = "";
      feedback.textContent = "Session mastery and review schedule reset. Nothing was saved.";
      hintNode.textContent = "Hints are available one step at a time.";
      renderMastery();
    });
    renderMastery();
    next();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
