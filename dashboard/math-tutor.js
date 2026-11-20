(function (root) {
  "use strict";

  const PREREQUISITES = Object.freeze({
    whole_number_arithmetic: [],
    fractions: ["whole_number_arithmetic"],
    decimals: ["whole_number_arithmetic"],
    integers: ["whole_number_arithmetic"],
    order_of_operations: ["whole_number_arithmetic", "integers"],
    ratios_and_proportions: ["fractions", "whole_number_arithmetic"],
    percentages: ["fractions", "decimals", "ratios_and_proportions"],
    pre_algebra: ["whole_number_arithmetic", "integers"],
    linear_equations: ["pre_algebra"],
    inequalities: ["linear_equations"],
    exponents_and_roots: ["whole_number_arithmetic"],
    basic_geometry: ["whole_number_arithmetic"],
    pythagorean_theorem: ["basic_geometry", "exponents_and_roots"],
    basic_statistics: ["whole_number_arithmetic"],
    median_and_range: ["basic_statistics"],
    basic_probability: ["fractions"],
    simple_interest: ["percentages"],
    unit_conversion: ["whole_number_arithmetic"]
  });
  const REVIEW_INTERVALS = Object.freeze([1, 2, 4, 8, 16]);
  const owns = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const copy = value => JSON.parse(JSON.stringify(value));

  function validateGraph(topics) {
    const keys = Object.keys(PREREQUISITES);
    if (keys.length !== topics.length || keys.some(key => !topics.includes(key))) {
      throw new Error("Prerequisite graph must cover every registered topic exactly once.");
    }
    const visiting = new Set(), visited = new Set();
    function visit(topic) {
      if (visiting.has(topic)) throw new Error("Prerequisite graph contains a cycle.");
      if (visited.has(topic)) return;
      visiting.add(topic);
      for (const dependency of PREREQUISITES[topic]) {
        if (!owns(PREREQUISITES, dependency)) throw new Error("Unknown prerequisite: " + dependency);
        visit(dependency);
      }
      visiting.delete(topic);
      visited.add(topic);
    }
    keys.forEach(visit);
    return true;
  }

  function createTutor(agent, reasoning) {
    if (!agent || !Array.isArray(agent.TOPIC_KEYS) || typeof agent.generate !== "function" || typeof agent.verify !== "function") {
      throw new Error("A compatible mathematics agent is required.");
    }
    validateGraph(agent.TOPIC_KEYS);
    let turn = 0;
    let seed = 1;
    const records = Object.create(null);
    agent.TOPIC_KEYS.forEach(topic => {
      records[topic] = { attempts: 0, correct: 0, streak: 0, bestStreak: 0, dueAt: null, lastAttemptAt: null };
    });

    function mastery(topic) {
      const record = records[topic];
      return record.attempts ? record.correct / record.attempts : 0;
    }
    function prerequisites(topic) {
      if (!owns(PREREQUISITES, topic)) throw new Error("Unknown mathematics topic.");
      return PREREQUISITES[topic].map(key => ({
        topic: key,
        attempts: records[key].attempts,
        mastery: mastery(key),
        ready: records[key].attempts >= 2 && mastery(key) >= 0.6
      }));
    }
    function getHints(topic, question) {
      if (!owns(PREREQUISITES, topic) || typeof question !== "string") throw new Error("A supported topic and question are required.");
      const solution = reasoning && typeof reasoning.reason === "function"
        ? reasoning.reason(agent, topic, question)
        : (() => { const solved = agent.solve(topic, question); return { kind: "solution", verified: agent.verify(topic, question, solved.answer), ...solved }; })();
      if (solution.kind !== "solution" || solution.verified !== true) return { available: false, hints: [], message: "ULTRON cannot provide hints for an unsupported or unverified question." };
      const knowledge = solution.knowledge || {};
      const steps = solution.steps || [];
      const hints = [
        { level: 1, title: "Recall the rule", text: knowledge.rule || "Identify the mathematical rule that matches this question." },
        { level: 2, title: "Choose a method", text: knowledge.method || "Choose a method that follows the rule and preserves exact values." },
        { level: 3, title: "Start the working", text: steps[0] || "Write the first operation before calculating." }
      ];
      return { available: true, topic, hints, verifiedSource: true, scope: "Hints are derived from the deterministic solver's independently verified solution; they are not a formal proof." };
    }
    function diagnose(topic, question, answer, work) {
      if (!owns(PREREQUISITES, topic) || typeof question !== "string" || typeof answer !== "string") {
        return { status: "invalid", message: "A supported topic, question and text answer are required.", misconception: null };
      }
      let expected;
      try {
        const report = reasoning && typeof reasoning.reason === "function"
          ? reasoning.reason(agent, topic, question)
          : { kind: "solution", answer: agent.solve(topic, question).answer, verified: agent.verify(topic, question, agent.solve(topic, question).answer) };
        if (report.kind !== "solution" || report.verified !== true) return { status: "unsupported", message: "This question is outside the verified foundation formats.", misconception: null };
        expected = report.answer;
      } catch (_) {
        return { status: "unsupported", message: "This question is outside the verified foundation formats.", misconception: null };
      }
      const correct = agent.verify(topic, question, answer.trim()) && answer.trim() === expected;
      if (correct) return { status: "correct", message: "Correct — the answer passed the independent checker.", expected, misconception: null };
      const hasWork = Array.isArray(work) && work.some(line => typeof line === "string" && line.trim());
      if (!hasWork) return {
        status: "incorrect_unclassified",
        message: "That answer did not pass the independent checker. I cannot identify the cause from the final answer alone; show your working for a more specific diagnosis.",
        expected,
        misconception: null
      };
      return {
        status: "incorrect_work_submitted",
        message: "The answer is not correct. Your working has been recorded only in this active session; this version does not yet classify individual error patterns.",
        expected,
        misconception: null,
        diagnosisLimit: "No misconception label is assigned until a validated step-by-step work parser exists."
      };
    }
    function recordAttempt(topic, correct) {
      if (!owns(records, topic) || typeof correct !== "boolean") throw new Error("Attempt requires a supported topic and boolean correctness.");
      turn += 1;
      const record = records[topic];
      record.attempts += 1;
      record.lastAttemptAt = turn;
      if (correct) {
        record.correct += 1;
        record.streak += 1;
        record.bestStreak = Math.max(record.bestStreak, record.streak);
        const interval = REVIEW_INTERVALS[Math.min(record.streak - 1, REVIEW_INTERVALS.length - 1)];
        record.dueAt = turn + interval;
      } else {
        record.streak = 0;
        record.dueAt = turn + REVIEW_INTERVALS[0];
      }
      return Object.freeze({ topic, turn, mastery: mastery(topic), streak: record.streak, dueAt: record.dueAt });
    }
    function dueTopics() {
      return agent.TOPIC_KEYS.filter(topic => records[topic].dueAt !== null && records[topic].dueAt <= turn);
    }
    function chooseTopic() {
      const due = dueTopics();
      const pool = due.length ? due : agent.TOPIC_KEYS.filter(topic => PREREQUISITES[topic].every(key => records[key].attempts >= 2 && mastery(key) >= 0.6));
      const candidates = pool.length ? pool : agent.TOPIC_KEYS.filter(topic => PREREQUISITES[topic].length === 0);
      return candidates.slice().sort((a, b) => {
        const ma = mastery(a), mb = mastery(b);
        if (ma !== mb) return ma - mb;
        if (records[a].attempts !== records[b].attempts) return records[a].attempts - records[b].attempts;
        return agent.TOPIC_KEYS.indexOf(a) - agent.TOPIC_KEYS.indexOf(b);
      })[0];
    }
    function nextExercise() {
      const topic = chooseTopic();
      const question = agent.generate(topic, seed++);
      const solution = reasoning && typeof reasoning.reason === "function"
        ? reasoning.reason(agent, topic, question)
        : { kind: "solution", answer: agent.solve(topic, question).answer, verified: agent.verify(topic, question, agent.solve(topic, question).answer) };
      if (solution.kind !== "solution" || solution.verified !== true) throw new Error("Generated exercise failed its verification gate.");
      return Object.freeze({ topic, question, seed: seed - 1, difficulty: "foundation_fixed", expectedAnswerAvailableToTutor: true });
    }
    function getSnapshot() {
      const topics = agent.TOPIC_KEYS.map(topic => ({
        topic,
        attempts: records[topic].attempts,
        correct: records[topic].correct,
        accuracy: mastery(topic),
        streak: records[topic].streak,
        bestStreak: records[topic].bestStreak,
        dueAt: records[topic].dueAt,
        prerequisites: PREREQUISITES[topic].slice()
      }));
      return Object.freeze({
        turn,
        topics,
        dueTopics: dueTopics(),
        storage: "memory_only",
        rawQuestionsPersisted: false,
        rawAnswersPersisted: false
      });
    }
    function reset() {
      turn = 0;
      seed = 1;
      agent.TOPIC_KEYS.forEach(topic => {
        records[topic] = { attempts: 0, correct: 0, streak: 0, bestStreak: 0, dueAt: null, lastAttemptAt: null };
      });
      return getSnapshot();
    }

    return Object.freeze({
      getHints,
      diagnose,
      recordAttempt,
      nextExercise,
      getSnapshot,
      getPrerequisites: prerequisites,
      reset,
      getCurrentTurn: () => turn
    });
  }

  const api = { PREREQUISITES, REVIEW_INTERVALS, validateGraph, createTutor };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ULTRON_MATH_TUTOR = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
