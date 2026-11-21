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
    const workingNode = document.getElementById("tutorWorking");
    const feedback = document.getElementById("tutorFeedback");
    const hintNode = document.getElementById("tutorHint");
    const masteryNode = document.getElementById("tutorMastery");
    const topicNode = document.getElementById("tutorTopic");
    const axiomContext = document.getElementById("tutorAxiomContext");
    let exercise = null;
    let hints = [];
    let hintIndex = 0;
    let answered = false;
    let verifiedTrace = null;

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
        verifiedTrace = null;
        topicNode.textContent = agent.TOPICS[exercise.topic].label + " · fixed foundation difficulty";
        axiomContext.replaceChildren();
        const relatedAxioms = window.ULTRON_AXIOM_BANK ? window.ULTRON_AXIOM_BANK.forTopic(exercise.topic) : [];
        const axiomHeading = document.createElement("strong");
        axiomHeading.textContent = "Related axioms";
        axiomContext.appendChild(axiomHeading);
        if (!relatedAxioms.length) {
          const empty = document.createElement("p");
          empty.textContent = "No direct axiom association is currently catalogued for this topic.";
          axiomContext.appendChild(empty);
        } else {
          const list = document.createElement("ul");
          relatedAxioms.slice(0, 3).forEach(item => {
            const entry = document.createElement("li");
            entry.textContent = item.id + " · " + item.name + " (" + item.systemLabel + ")";
            list.appendChild(entry);
          });
          axiomContext.appendChild(list);
        }
        questionNode.textContent = exercise.question;
        answerNode.value = "";
        workingNode.value = "";
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
      const diagnosis = tutor.diagnose(exercise.topic, exercise.question, answerNode.value, workingNode.value.split("\n").filter(line => line.trim()), verifiedTrace);
      if (!["correct", "incorrect_unclassified", "incorrect_work_submitted"].includes(diagnosis.status)) {
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
      axiomContext.textContent = "Related axioms appear when a question is active.";
      questionNode.textContent = "Choose New question to begin.";
      answerNode.value = "";
      workingNode.value = "";
      feedback.textContent = "Session mastery and review schedule reset. Nothing was saved.";
      hintNode.textContent = "Hints are available one step at a time.";
      renderMastery();
    });
    const traceInput = document.getElementById("proofTraceInput");
    const traceResult = document.getElementById("proofTraceResult");
    const traceExample = {
      kind: "ultron-proof-trace",
      proof: {
        version: 1, system: "PEANO_N", assumptions: [],
        steps: [{
          id: "reflexive-equality", rule: "eq_refl",
          term: { kind: "nat", value: 2 },
          formula: { kind: "eq", left: { kind: "nat", value: 2 }, right: { kind: "nat", value: 2 } }
        }],
        conclusion: "reflexive-equality"
      },
      claimedConclusion: { kind: "eq", left: { kind: "nat", value: 2 }, right: { kind: "nat", value: 2 } }
    };
    const exampleButton = document.getElementById("proofTraceExampleButton");
    const checkButton = document.getElementById("proofTraceCheckButton");
    if (exampleButton && traceInput) exampleButton.addEventListener("click", () => {
      traceInput.value = JSON.stringify(traceExample, null, 2);
      verifiedTrace = null;
      if (traceResult) traceResult.textContent = "Example loaded. Select Verify proof trace to replay it.";
    });
    if (checkButton && traceInput && traceResult) checkButton.addEventListener("click", () => {
      try {
        const parsed = JSON.parse(traceInput.value);
        const result = tutor.validateWorkingTrace(parsed);
        verifiedTrace = result.valid ? parsed : null;
        traceResult.textContent = result.valid
          ? "VALID · " + result.system + " · " + result.checkedSteps + " steps · open assumptions: " + (result.openAssumptions.join(", ") || "none") + " · axiom dependencies: " + (result.usedAxioms.join(", ") || "none") + "\nThe trace may be used as verified evidence; it is not automatically a diagnosis."
          : "REJECTED · " + result.code + " · " + result.message;
      } catch (error) {
        verifiedTrace = null;
        traceResult.textContent = "INVALID JSON · " + (error.message || "Could not parse proof trace.");
      }
    });
    renderMastery();
    next();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
