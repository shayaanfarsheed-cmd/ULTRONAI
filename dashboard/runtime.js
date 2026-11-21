(function (root) {
  "use strict";

  function scheduleFrame(draw, environment) {
    if (typeof draw !== "function") throw new TypeError("A drawing callback is required.");
    const env = environment || root;
    if (env && typeof env.requestAnimationFrame === "function") {
      return env.requestAnimationFrame(draw);
    }
    draw();
    return null;
  }

  const api = Object.freeze({scheduleFrame});
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ULTRON_RUNTIME = api;
})(typeof window !== "undefined" ? window : globalThis);
