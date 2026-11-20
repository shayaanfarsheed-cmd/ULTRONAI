(function () {
  "use strict";
  function init() {
    const bank = window.ULTRON_AXIOM_BANK;
    const search = document.getElementById("axiomSearch");
    const results = document.getElementById("axiomResults");
    const detail = document.getElementById("axiomDetail");
    const count = document.getElementById("axiomCount");
    if (!bank || !search || !results || !detail) return;
    function renderDetail(entry) {
      detail.replaceChildren();
      if (!entry) { detail.textContent = "Choose an axiom to inspect its formal statement, scope and sources."; return; }
      const heading = document.createElement("h3");
      heading.textContent = entry.id + " · " + entry.name;
      detail.appendChild(heading);
      const system = document.createElement("p");
      system.textContent = "Formal system: " + entry.systemLabel + " · Domain: " + entry.domain;
      detail.appendChild(system);
      const formal = document.createElement("p");
      formal.className = "axiom-formal";
      formal.textContent = entry.formal;
      detail.appendChild(formal);
      for (const [label, value] of [["Meaning", entry.meaning], ["Teaching note", entry.teaching]]) {
        const paragraph = document.createElement("p");
        paragraph.textContent = label + ": " + value;
        detail.appendChild(paragraph);
      }
      const scope = document.createElement("p");
      scope.className = "fine-print";
      scope.textContent = "Scope warning: valid only within the named formal system and domain. An axiom is an assumption, not a theorem proved from other assumptions.";
      detail.appendChild(scope);
      const sources = document.createElement("ul");
      sources.className = "axiom-source-list";
      entry.references.forEach((url, index) => {
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Research source " + (index + 1);
        li.appendChild(link);
        sources.appendChild(li);
      });
      detail.appendChild(sources);
    }
    function render() {
      const matches = bank.list({ query: search.value.trim() });
      results.replaceChildren();
      count.textContent = matches.length + " / " + bank.count + " entries";
      matches.forEach(entry => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "axiom-result";
        button.textContent = entry.id + " · " + entry.name + " (" + entry.systemLabel + ")";
        button.addEventListener("click", () => renderDetail(entry));
        results.appendChild(button);
      });
      if (!matches.length) results.textContent = "No matching axioms.";
    }
    search.addEventListener("input", render);
    render();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
