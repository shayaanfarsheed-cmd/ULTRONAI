(function (root) {
  "use strict";

  const MAX_TURNS = 20;
  const MAX_INPUT_LENGTH = 1000;
  const TOPIC_ALIASES = {
    whole_number_arithmetic: ["whole number", "whole-number", "arithmetic"],
    fractions: ["fraction", "fractions"],
    decimals: ["decimal", "decimals"],
    percentages: ["percent", "percentage", "percentages"],
    ratios_and_proportions: ["ratio", "ratios", "proportion", "proportions"],
    integers: ["integer", "integers", "negative number", "negative numbers"],
    order_of_operations: ["order of operations", "bodmas", "pemdas"],
    pre_algebra: ["pre algebra", "pre-algebra", "one-step equation"],
    linear_equations: ["linear equation", "linear equations", "equation", "equations"],
    inequalities: ["inequality", "inequalities"],
    exponents_and_roots: ["exponent", "exponents", "square root", "roots", "powers"],
    basic_geometry: ["geometry", "rectangle", "area", "perimeter"],
    basic_statistics: ["statistics", "mean", "average"],
    basic_probability: ["probability"],
    median_and_range: ["median", "range"],
    simple_interest: ["simple interest", "interest"],
    unit_conversion: ["unit conversion", "convert units", "metric conversion"],
    pythagorean_theorem: ["pythagorean", "right triangle"]
  };

  function normalizeArithmetic(text) {
    const cleaned = text.trim().replace(/[?!.]+$/, "");
    const match = /^(?:(?:what is|calculate|compute|evaluate)\s+)?([+-]?\d+(?:\.\d+)?(?:\s*\/\s*\d+)?\s*[+*/-]\s*[+-]?\d+(?:\.\d+)?(?:\s*\/\s*\d+)?)$/i.exec(cleaned);
    if (!match) return null;
    const expression = match[1].replace(/\s+/g, " ");
    if (/\d+\.\d+/.test(expression)) return { topic: "decimals", question: "Calculate: " + expression };
    if (/\d+\s*\/\s*\d+/.test(expression)) {
      const fractionMatch = /^\(?([+-]?\d+\s*\/\s*\d+)\)?\s*([+*/-])\s*\(?([+-]?\d+\s*\/\s*\d+)\)?$/.exec(expression);
      if (fractionMatch) return { topic: "fractions", question: "Calculate: (" + fractionMatch[1].replace(/\s/g, "") + ") " + fractionMatch[2] + " (" + fractionMatch[3].replace(/\s/g, "") + ")" };
      if (/^[+-]?\d+\s*\/\s*[+-]?\d+$/.test(expression)) {
        const signedDivision = /(^|\s)-\d/.test(expression);
        return { topic: signedDivision ? "integers" : "whole_number_arithmetic", question: "Calculate: " + expression };
      }
      return null;
    }
    const signed = /(^|\s)-\d/.test(expression);
    return { topic: signed ? "integers" : "whole_number_arithmetic", question: "Calculate: " + expression };
  }

  function createConversation(agent, options) {
    if (!agent || typeof agent.solve !== "function" || typeof agent.verify !== "function" || !agent.TOPICS) {
      throw new TypeError("A compatible ULTRON math agent is required.");
    }
    const settings = options || {};
    const maxTurns = Number.isInteger(settings.maxTurns) ? Math.max(1, Math.min(settings.maxTurns, MAX_TURNS)) : MAX_TURNS;
    let history = [];
    let lastTopic = null;

    function append(turn) {
      history.push(turn);
      if (history.length > maxTurns * 2) history = history.slice(-maxTurns * 2);
    }

    function containsPhrase(text, phrase) {
      const target = phrase.toLowerCase();
      let offset = 0;
      while (offset < text.length) {
        const index = text.indexOf(target, offset);
        if (index < 0) return false;
        const before = index === 0 || !/[a-z]/i.test(text[index - 1]);
        const afterIndex = index + target.length;
        const after = afterIndex === text.length || !/[a-z]/i.test(text[afterIndex]);
        if (before && after) return true;
        offset = index + 1;
      }
      return false;
    }

    function detectTopic(input) {
      const lower = input.toLowerCase();
      for (const key of Object.keys(TOPIC_ALIASES)) {
        if (!agent.TOPICS[key]) continue;
        const aliases = [key.replace(/_/g, " "), agent.TOPICS[key].label].concat(TOPIC_ALIASES[key]);
        if (aliases.some(alias => containsPhrase(lower, alias))) return key;
      }
      return null;
    }

    function clarification(message, topic) {
      const chosenTopic = topic || lastTopic;
      const example = chosenTopic && agent.TOPICS[chosenTopic] ? agent.generate(chosenTopic, 1) : null;
      return {
        kind: "clarification",
        message: message || "I need one detail before I can solve that.",
        topic: chosenTopic,
        example,
        verified: false
      };
    }

    function reply(rawInput) {
      if (typeof rawInput !== "string") throw new TypeError("Enter a text question.");
      const input = rawInput.trim();
      if (!input) throw new Error("Enter a question.");
      if (input.length > MAX_INPUT_LENGTH) throw new Error("Keep each message to 1,000 characters or fewer.");
      append({ role: "user", text: input, timestamp: Date.now() });

      if (/^(help|\/help)$/i.test(input)) {
        const response = clarification("I can solve supported foundation maths questions. Include a topic name, or ask a simple arithmetic expression. I will ask when the topic or format is unclear.");
        append({ role: "assistant", ...response, timestamp: Date.now() });
        return response;
      }
      if (/^(reset|\/reset)$/i.test(input)) {
        lastTopic = null;
        history = [];
        const response = { kind: "notice", message: "This conversation has been reset. No chat history was saved.", verified: false };
        append({ role: "assistant", ...response, timestamp: Date.now() });
        return response;
      }

      const arithmetic = normalizeArithmetic(input);
      const prefix = /^([^:]{1,80}):\s*/.exec(input);
      const prefixedTopic = prefix ? detectTopic(prefix[1]) : null;
      const detectedTopic = detectTopic(input);
      let topic = prefixedTopic || detectedTopic || (arithmetic && arithmetic.topic) || lastTopic;
      let question = arithmetic ? arithmetic.question : input;
      if (prefixedTopic) question = input.slice(prefix[0].length).trim();
      if (!topic) {
        const response = clarification("Which maths topic is this about? For example: fractions, decimals, percentages, linear equations or geometry. You can also ask a simple arithmetic expression such as “What is 12 + 5?”");
        append({ role: "assistant", ...response, timestamp: Date.now() });
        return response;
      }
      if (!question || question === input && !/^(calculate|solve|find|convert|evaluate)\s*:/i.test(question)) {
        const response = clarification("I identified " + agent.TOPICS[topic].label + ", but I need the question in a supported format.", topic);
        append({ role: "assistant", ...response, timestamp: Date.now() });
        return response;
      }
      try {
        const solved = agent.solve(topic, question);
        const verified = agent.verify(topic, question, solved.answer);
        const response = {
          kind: verified ? "solution" : "unverified",
          topic,
          topicLabel: agent.TOPICS[topic].label,
          answer: solved.answer,
          knowledge: solved.knowledge,
          steps: solved.steps.slice(),
          verified: Boolean(verified),
          message: verified ? "The independent answer check passed." : "The independent answer check did not pass. Do not rely on this result."
        };
        lastTopic = topic;
        append({ role: "assistant", ...response, timestamp: Date.now() });
        return response;
      } catch (error) {
        const response = clarification(error && error.message ? error.message : "I could not parse that question.", topic);
        append({ role: "assistant", ...response, timestamp: Date.now() });
        return response;
      }
    }

    return {
      reply,
      reset() { history = []; lastTopic = null; },
      getHistory() { return history.map(turn => ({ ...turn })); },
      getLastTopic() { return lastTopic; },
      maxTurns
    };
  }

  const api = { MAX_TURNS, MAX_INPUT_LENGTH, createConversation, normalizeArithmetic };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ULTRON_CONVERSATION = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
