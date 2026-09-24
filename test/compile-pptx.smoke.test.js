import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const compiler = join(packageRoot, "lib", "compile-pptx.py");
const template = join(packageRoot, "lib", "assets", "base-template.pptx");
const validator = join(packageRoot, "test", "helpers", "validate_pptx.py");
const fixture = join(packageRoot, "test", "fixtures", "smoke-deck");

function pythonCandidates() {
  return process.platform === "win32" ? ["python", "python3", "py"] : ["python3", "python"];
}

function runPython(script, args) {
  for (const pyExec of pythonCandidates()) {
    const result = spawnSync(pyExec, [script, ...args], { encoding: "utf8" });
    if (result.error && result.error.code === "ENOENT") continue;
    return result;
  }
  return null;
}

test("compile-pptx produces a structurally valid native pptx", { skip: !existsSync(compiler) || !existsSync(template) ? "compiler or bundled template missing" : false }, (t) => {
  const workDir = mkdtempSync(join(tmpdir(), "okp-smoke-"));
  t.after(() => rmSync(workDir, { recursive: true, force: true }));
  const output = join(workDir, "smoke.pptx");

  const compile = runPython(compiler, [fixture, "--output", output]);
  assert.ok(compile, "no python3 interpreter found");
    assert.equal(
      compile.status,
      0,
      `compiler failed:\nstdout: ${compile.stdout}\nstderr: ${compile.stderr}`,
    );
  assert.ok(existsSync(output), "output pptx was not created");

  // 2 slides; page 2 pairs a chart with an animation targeting the chart
  // element itself, which must not emit a dangling spid reference.
  const validate = runPython(validator, [output, "2"]);
  assert.ok(validate, "no python3 interpreter found");
  assert.equal(
    validate.status,
    0,
    `validation failed:\nstdout: ${validate.stdout}\nstderr: ${validate.stderr}`,
  );
  assert.match(validate.stdout, /VALIDATE OK: 2 slides/);
});
