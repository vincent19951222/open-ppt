import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("Mindray Red restyling preserves native business content and validates layout plans", () => {
  const candidates = process.platform === "win32" ? ["python", "python3", "py"] : ["python3", "python"];
  let result;
  for (const executable of candidates) {
    result = spawnSync(executable, ["-X", "utf8", join(root, "skills/open-ppt/tests/test_restyle_pptx.py")], { encoding: "utf8" });
    if (result.error?.code === "ENOENT") continue;
    break;
  }
  assert.ok(result && !result.error, `Python required: ${result?.error?.message}`);
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
