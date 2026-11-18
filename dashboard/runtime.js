(function (root) {
  "use strict";
  const MAX_METADATA_BYTES = 1024 * 1024;
  const MAX_FILE_BYTES = 64 * 1024 * 1024;
  const MAX_TOTAL_BYTES = 256 * 1024 * 1024;

  async function mapWithConcurrency(items, limit, mapper) {
    const results = new Array(items.length);
    let nextIndex = 0;
    const workerCount = Math.min(Math.max(1, Math.floor(limit) || 1), items.length);
    await Promise.all(Array.from({length: workerCount}, async function () {
      while (true) {
        const index = nextIndex++;
        if (index >= items.length) return;
        results[index] = await mapper(items[index], index);
      }
    }));
    return results;
  }

  function validateManifest(manifest, checkpointId) {
    if (!manifest || Object.getPrototypeOf(manifest) !== Object.prototype ||
        manifest.checkpoint_id !== checkpointId ||
        !/^ckpt-[A-Za-z0-9_-]{1,80}$/.test(checkpointId) ||
        !Number.isSafeInteger(Number(manifest.step)) || Number(manifest.step) < 0 ||
        !manifest.files || Object.getPrototypeOf(manifest.files) !== Object.prototype) {
      throw new Error("Checkpoint manifest structure is invalid.");
    }
    const names = Object.keys(manifest.files);
    if (!names.length || names.length > 64) throw new Error("Checkpoint file count is outside the allowed limit.");
    let total = 0;
    for (const name of names) {
      const entry = manifest.files[name];
      if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(name) || name === "." || name === ".." ||
          !entry || Object.getPrototypeOf(entry) !== Object.prototype ||
          !Number.isSafeInteger(entry.size_bytes) || entry.size_bytes < 0 ||
          entry.size_bytes > MAX_FILE_BYTES || !/^[a-f0-9]{64}$/i.test(entry.sha256 || "")) {
        throw new Error("Checkpoint file metadata is invalid: " + name);
      }
      total += entry.size_bytes;
      if (!Number.isSafeInteger(total) || total > MAX_TOTAL_BYTES) {
        throw new Error("Checkpoint exceeds the 256 MiB total size limit.");
      }
    }
    if (!Object.prototype.hasOwnProperty.call(manifest.files, "state.json")) {
      throw new Error("Checkpoint state file is missing.");
    }
    return {totalBytes: total, fileCount: names.length};
  }

  function scheduleFrame(draw, environment) {
    const env = environment || root;
    if (env && typeof env.requestAnimationFrame === "function") {
      return env.requestAnimationFrame(draw);
    }
    draw();
    return null;
  }

  function createSingleFlight() {
    let pending = null;
    const run = function (operation) {
      if (pending) return pending;
      const current = Promise.resolve().then(operation);
      pending = current;
      return current.finally(function () {
        if (pending === current) pending = null;
      });
    };
    run.reset = function () { pending = null; };
    return run;
  }

  const api = {mapWithConcurrency, validateManifest, scheduleFrame, createSingleFlight,
    MAX_METADATA_BYTES, MAX_FILE_BYTES, MAX_TOTAL_BYTES};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ULTRON_RUNTIME = api;
})(typeof window !== "undefined" ? window : globalThis);
