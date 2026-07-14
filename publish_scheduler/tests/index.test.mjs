import test from "node:test";
import assert from "node:assert/strict";

test("scheduler contract names the single publish dispatch event", async () => {
  const source = await (await import("node:fs/promises")).readFile(new URL("../src/index.ts", import.meta.url), "utf8");
  assert.match(source, /threads_publish_scheduled/);
  assert.match(source, /snapshot_commit/);
  assert.match(source, /MAX_DISPATCH_ATTEMPTS = 3/);
});
