(function () {
  "use strict";

  function init() {
    const agent = window.ULTRON_MATH_AGENT;
    const conversationApi = window.ULTRON_CONVERSATION;
    const form = document.getElementById("mathConversationForm");
    if (!agent || !conversationApi || !form) return;

    const input = document.getElementById("mathConversationInput");
    const transcript = document.getElementById("mathConversationTranscript");
    const send = document.getElementById("mathConversationSend");
    const reset = document.getElementById("mathConversationReset");
    const status = document.getElementById("mathConversationStatus");
    const chat = conversationApi.createConversation(agent);

    function addText(parent, tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      node.textContent = text;
      parent.appendChild(node);
      return node;
    }

    function render() {
      transcript.replaceChildren();
      chat.getHistory().forEach(turn => {
        const message = document.createElement("article");
        message.className = "conversation-message " + (turn.role === "user" ? "conversation-user" : "conversation-assistant");
        addText(message, "div", "conversation-role", turn.role === "user" ? "YOU" : "ULTRON");
        if (turn.role === "user") {
          addText(message, "p", "conversation-copy", turn.text);
        } else {
          addText(message, "p", "conversation-copy", turn.message || "");
          if (turn.kind === "solution" || turn.kind === "unverified") {
            addText(message, "div", "conversation-topic", turn.topicLabel || turn.topic || "Mathematics");
            if (turn.reasoning && turn.reasoning.problem) {
              addText(
                message,
                "p",
                "conversation-reasoning-summary",
                "Structured problem · " + turn.reasoning.problem.problemType + " · domain: " + turn.reasoning.problem.domain
              );
            }
            addText(message, "p", "conversation-answer", turn.answer);
            if (turn.knowledge) {
              addText(message, "strong", "conversation-concept", turn.knowledge.concept);
              addText(message, "p", "conversation-detail", "Rule: " + turn.knowledge.rule);
              addText(message, "p", "conversation-detail", "Method: " + turn.knowledge.method);
            }
            if (turn.steps && turn.steps.length) {
              const list = document.createElement("ol");
              list.className = "conversation-steps";
              turn.steps.forEach(step => addText(list, "li", "", step));
              message.appendChild(list);
            }
            addText(message, "span", turn.verified ? "conversation-verification is-verified" : "conversation-verification", turn.verified ? "INDEPENDENT CHECK PASSED" : "NOT VERIFIED");
          }
          if (turn.example) {
            const example = document.createElement("button");
            example.type = "button";
            example.className = "quiet-button conversation-example";
            example.textContent = "Use example";
            example.addEventListener("click", () => {
              const label = turn.topic && agent.TOPICS[turn.topic] ? agent.TOPICS[turn.topic].label : "";
              input.value = label ? label + ": " + turn.example : turn.example;
              input.focus();
            });
            message.appendChild(example);
          }
        }
        transcript.appendChild(message);
      });
      transcript.scrollTop = transcript.scrollHeight;
    }

    form.addEventListener("submit", event => {
      event.preventDefault();
      if (send.disabled) return;
      send.disabled = true;
      try {
        const result = chat.reply(input.value);
        input.value = "";
        status.textContent = result.verified ? "Solved and independently verified." :
          result.kind === "clarification" ? "Clarification needed. ULTRON has not guessed." : result.message;
        render();
      } catch (error) {
        status.textContent = error.message || "Message could not be processed.";
      } finally {
        send.disabled = false;
        input.focus();
      }
    });

    reset.addEventListener("click", () => {
      chat.reset();
      transcript.replaceChildren();
      addText(transcript, "p", "empty-state", "Conversation reset. No chat history was saved.");
      status.textContent = "Ready for a new mathematics question.";
      input.value = "";
      input.focus();
    });

    addText(transcript, "p", "empty-state", "Start with a simple arithmetic question, or name a topic such as fractions, decimals or geometry. ULTRON will ask for clarification when it cannot safely identify the question.");
    status.textContent = "Local session only · maximum 20 user/assistant turns · no automatic training or durable chat storage.";
  }

  document.addEventListener("DOMContentLoaded", init);
})();
