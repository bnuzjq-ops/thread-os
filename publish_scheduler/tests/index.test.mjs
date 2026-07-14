import test from "node:test";
import assert from "node:assert/strict";

test("scheduler contract names the single publish dispatch event", async () => {
  const source = await (await import("node:fs/promises")).readFile(new URL("../src/index.ts", import.meta.url), "utf8");
  assert.match(source, /threads_publish_scheduled/);
  assert.match(source, /snapshot_commit/);
  assert.match(source, /MAX_DISPATCH_ATTEMPTS = 3/);
});

test("scheduler alert failures are visible and do not depend on a custom label", async () => {
  const source = await (await import("node:fs/promises")).readFile(new URL("../src/index.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /labels: \["publish-alert"\]/);
  assert.match(source, /if \(!response\.ok\)/);
  assert.match(source, /GitHub issue creation failed/);
});

test("lead-time validation applies only when registering a schedule", async () => {
  const source = await (await import("node:fs/promises")).readFile(new URL("../src/index.ts", import.meta.url), "utf8");
  assert.match(source, /validateSchedule\(event\.payload, false\)/);
  assert.match(source, /validateSchedule\(await request\.json\(\) as ScheduleParams, true\)/);
  assert.match(source, /if \(requireLeadTime && scheduled - Date\.now\(\) < MIN_LEAD_MS\)/);
});
