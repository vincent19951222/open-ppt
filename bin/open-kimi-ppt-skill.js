#!/usr/bin/env node

import { cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, renameSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join, resolve, sep } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { stdin as input, stdout as output } from "node:process";
import { fileURLToPath } from "node:url";
import { startEditorServer } from "../lib/editor-server.js";

const SKILL_NAME = "open-kimi-ppt";
const MIN_NODE_MAJOR = 18;
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceDirectory = join(packageRoot, "skills", SKILL_NAME);
const packageVersion = JSON.parse(readFileSync(join(packageRoot, "package.json"), "utf8")).version;

const KNOWN_TARGETS = [
  { id: "agents", label: "Shared / default", relative: [".agents", "skills"] },
  { id: "codex", label: "Codex", relative: [".codex", "skills"] },
  { id: "claude", label: "Claude Code", relative: [".claude", "skills"] },
  { id: "cursor", label: "Cursor", relative: [".cursor", "skills"] },
  { id: "workbuddy", label: "WorkBuddy", relative: [".workbuddy", "skills"] },
];

function assertNodeVersion() {
  const major = Number.parseInt(process.versions.node.split(".")[0], 10);
  if (!Number.isInteger(major) || major < MIN_NODE_MAJOR) {
    throw new Error(
      `Node.js ${MIN_NODE_MAJOR}+ is required; found ${process.version}. Install from https://nodejs.org`,
    );
  }
}

function printHelp(command) {
  if (command === "serve" || command === "preview") {
    console.log(`Start the local PPTD editor with direct project preview.

Usage:
  open-kimi-ppt-skill serve [project-directory] [options]
  open-kimi-ppt-skill preview <project-directory> [options]

Options:
  --project <dir>  Mount and directly preview a PPTD project
  --port <number>  HTTP port (default: 55173)
  --open           Open in the default browser (default: true when project specified)
  -h, --help       Show this help
  -V, --version    Show version
`);
    return;
  }

  if (command === "compile") {
    console.log(`Compile a PPTD project directly into a native .pptx (local, no browser).

Usage:
  open-kimi-ppt-skill compile <project-directory-or-.pptd> [options]

Options:
  -o, --output <file>  Output .pptx path (default: next to the .pptd manifest)
  -h, --help           Show this help
  -V, --version        Show version

Requires python3 with PyYAML (auto-installed with pip --user when missing).
`);
    return;
  }

  console.log(`Install ${SKILL_NAME} for your AI coding agent or start its local editor.

Usage:
  open-kimi-ppt-skill [install] [options]
  open-kimi-ppt-skill serve [project-directory] [options]
  open-kimi-ppt-skill preview <project-directory> [options]
  open-kimi-ppt-skill compile <project-directory-or-.pptd> [options]

Install options:
  --target <directory>  Skills directory (repeatable)
  -y, --yes             Non-interactive; install to ~/.agents/skills when no --target
  --all                 Install to all detected agent skill directories
                        (agents whose home directory is missing are skipped)
  -h, --help            Show this help
  -V, --version         Show version

In an interactive terminal (no --target / --yes / --all), a checklist is shown:
  ↑/↓ move  space select  a all  enter confirm

For agents / CI, prefer:
  npx open-kimi-ppt-skill@latest install -y

Re-running install replaces an existing open-kimi-ppt installation.
Run "open-kimi-ppt-skill serve --help" for server options.
`);
}

function printVersion() {
  console.log(packageVersion);
}

function parseArguments(arguments_) {
  const args = [...arguments_];
  const command = args[0] === "install" || args[0] === "serve" || args[0] === "preview" || args[0] === "compile" ? args.shift() : "install";
  const isServerCommand = command === "serve" || command === "preview";
  const options = isServerCommand
    ? { command, open: command === "preview", port: 55173, project: null }
    : command === "compile"
      ? { command, input: null, output: null }
      : { command, targets: [], yes: false, all: false };

  while (args.length > 0) {
    const argument = args.shift();

    // Accepted for backward compatibility; install always overwrites.
    if (command === "install" && argument === "--force") {
      continue;
    }

    if (command === "install" && (argument === "-y" || argument === "--yes")) {
      options.yes = true;
      continue;
    }

    if (command === "install" && argument === "--all") {
      options.all = true;
      continue;
    }

    if (command === "install" && argument === "--target") {
      const target = args.shift();
      if (!target || target.startsWith("-")) {
        throw new Error("--target requires a directory");
      }
      options.targets.push(resolve(target));
      continue;
    }

    if (command === "compile" && (argument === "-o" || argument === "--output")) {
      const target = args.shift();
      if (!target || target.startsWith("-")) {
        throw new Error("--output requires a file path");
      }
      options.output = target;
      continue;
    }

    if (command === "compile" && !argument.startsWith("-") && !options.input) {
      options.input = argument;
      continue;
    }

    if (isServerCommand && (argument === "--project" || argument === "-p")) {
      const project = args.shift();
      if (!project || project.startsWith("-")) {
        throw new Error("--project requires a directory");
      }
      options.project = project;
      options.open = true;
      continue;
    }

    if (isServerCommand && argument === "--port") {
      const port = Number(args.shift());
      if (!Number.isInteger(port) || port < 1 || port > 65_535) {
        throw new Error("--port must be an integer between 1 and 65535");
      }
      options.port = port;
      continue;
    }

    if (isServerCommand && argument === "--open") {
      options.open = true;
      continue;
    }

    if (isServerCommand && !argument.startsWith("-") && !options.project) {
      options.project = argument;
      options.open = true;
      continue;
    }

    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }

    if (argument === "--version" || argument === "-V") {
      options.version = true;
      continue;
    }

    throw new Error(`unknown argument: ${argument}`);
  }

  return options;
}

function openBrowser(url) {
  const command = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.on("error", (error) => console.warn(`Could not open the browser: ${error.message}`));
  child.unref();
}

function defaultSkillsDirectory() {
  return join(homedir(), ".agents", "skills");
}

function knownTargetDirectories() {
  const home = homedir();
  return KNOWN_TARGETS.map((entry) => ({
    ...entry,
    directory: join(home, ...entry.relative),
  }));
}

function displayPath(absolutePath) {
  const home = homedir();
  const normalized = absolutePath.split(sep).join("/");
  const homeNormalized = home.split(sep).join("/");
  if (normalized === homeNormalized || normalized.startsWith(`${homeNormalized}/`)) {
    return `~${normalized.slice(homeNormalized.length)}`;
  }
  return absolutePath;
}

function isInteractiveInstall() {
  return Boolean(input.isTTY && output.isTTY);
}

function uniqueDirectories(directories) {
  const seen = new Set();
  const unique = [];
  for (const directory of directories) {
    const key = resolve(directory);
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(key);
  }
  return unique;
}

async function promptInstallTargets() {
  const choices = knownTargetDirectories();
  const selected = new Set([0]);
  let cursor = 0;
  const lines = choices.length + 3;

  const render = (initial = false) => {
    if (!initial) {
      output.write(`\u001b[${lines}A`);
    }
    output.write("Install open-kimi-ppt to which skills directories?\n");
    output.write("↑/↓ move · space select · a all · enter confirm · ctrl+c cancel\n");
    for (const [index, choice] of choices.entries()) {
      const pointer = index === cursor ? "❯" : " ";
      const mark = selected.has(index) ? "◉" : "◯";
      const installed = existsSync(join(choice.directory, SKILL_NAME, "SKILL.md"))
        ? " (installed)"
        : "";
      const line = `${pointer}${mark} ${displayPath(choice.directory).padEnd(28)} ${choice.label}${installed}`;
      output.write(`\u001b[2K${line}\n`);
    }
  };

  return new Promise((resolvePromise, reject) => {
    if (typeof input.setRawMode !== "function") {
      resolvePromise([defaultSkillsDirectory()]);
      return;
    }

    render(true);
    input.setRawMode(true);
    input.resume();
    input.setEncoding("utf8");

    const cleanup = () => {
      input.off("data", onData);
      input.setRawMode(false);
      input.pause();
    };

    const onData = (key) => {
      if (key === "\u0003") {
        cleanup();
        output.write("\n");
        reject(new Error("install cancelled"));
        return;
      }

      if (key === "\u001b[A" || key === "k") {
        cursor = (cursor - 1 + choices.length) % choices.length;
        render();
        return;
      }

      if (key === "\u001b[B" || key === "j") {
        cursor = (cursor + 1) % choices.length;
        render();
        return;
      }

      if (key === " ") {
        if (selected.has(cursor)) selected.delete(cursor);
        else selected.add(cursor);
        render();
        return;
      }

      if (key === "a" || key === "A") {
        if (selected.size === choices.length) selected.clear();
        else for (let index = 0; index < choices.length; index += 1) selected.add(index);
        render();
        return;
      }

      if (key === "\r" || key === "\n") {
        if (selected.size === 0) {
          output.write("\u0007");
          return;
        }
        cleanup();
        output.write("\n");
        resolvePromise([...selected].sort((a, b) => a - b).map((index) => choices[index].directory));
      }
    };

    input.on("data", onData);
  });
}

function detectedTargetDirectories() {
  const home = homedir();
  const detected = [];
  const skipped = [];
  for (const entry of knownTargetDirectories()) {
    if (existsSync(join(home, entry.relative[0]))) detected.push(entry);
    else skipped.push(entry);
  }
  return { detected, skipped };
}

async function resolveInstallTargets(options) {
  if (options.targets.length > 0) {
    return uniqueDirectories(options.targets);
  }

  if (options.all) {
    const { detected, skipped } = detectedTargetDirectories();
    for (const entry of skipped) {
      console.log(`Skipped ${entry.directory} (${entry.label} not found)`);
    }
    if (detected.length === 0) {
      console.warn(
        "No known agent directories found; nothing installed. Use -y for ~/.agents/skills or --target <directory>.",
      );
    }
    return uniqueDirectories(detected.map((entry) => entry.directory));
  }

  if (options.yes || !isInteractiveInstall()) {
    return [defaultSkillsDirectory()];
  }

  return promptInstallTargets();
}

function installSkillTo(skillsDirectory) {
  if (!existsSync(join(sourceDirectory, "SKILL.md"))) {
    throw new Error(`packaged skill is incomplete: ${sourceDirectory}`);
  }

  const destination = join(skillsDirectory, SKILL_NAME);
  const replaced = existsSync(destination);

  mkdirSync(skillsDirectory, { recursive: true });
  const stagingRoot = mkdtempSync(join(skillsDirectory, `.${SKILL_NAME}-`));
  const stagedSkill = join(stagingRoot, SKILL_NAME);

  try {
    cpSync(sourceDirectory, stagedSkill, {
      recursive: true,
      filter: (source) => ![".DS_Store", "_user_meta.json"].includes(basename(source)),
    });

    rmSync(destination, { recursive: true, force: true });
    try {
      renameSync(stagedSkill, destination);
    } catch (error) {
      if (error.code === "EPERM" || error.code === "EACCES") {
        // Windows file locks may briefly linger after rmSync
        cpSync(stagedSkill, destination, { recursive: true });
      } else {
        throw error;
      }
    }
  } finally {
    rmSync(stagingRoot, { recursive: true, force: true });
  }

  console.log(
    replaced
      ? `Updated ${SKILL_NAME} at ${destination}`
      : `Installed ${SKILL_NAME} to ${destination}`,
  );
}

async function installSkill(options) {
  const targets = await resolveInstallTargets(options);
  for (const target of targets) {
    installSkillTo(target);
  }
}

function pythonCandidates() {
  return process.platform === "win32" ? ["python", "python3", "py"] : ["python3", "python"];
}

function runCompilerWith(pyExec, args) {
  return spawnSync(pyExec, [join(packageRoot, "lib", "compile-pptx.py"), ...args], {
    encoding: "utf8",
  });
}

function runCompile(options) {
  if (!options.input) {
    throw new Error("compile requires a project directory or .pptd manifest path");
  }
  const args = [resolve(options.input)];
  if (options.output) args.push("--output", resolve(options.output));

  let lastError = null;
  for (const pyExec of pythonCandidates()) {
    let result = runCompilerWith(pyExec, args);
    if (result.error && result.error.code === "ENOENT") {
      lastError = result.error;
      continue;
    }
    if (/ModuleNotFoundError: No module named 'yaml'/i.test(result.stderr || "")) {
      console.log("PyYAML missing; installing with pip --user …");
      const install = spawnSync(pyExec, ["-m", "pip", "install", "--user", "pyyaml"], { encoding: "utf8" });
      if (install.status === 0) {
        result = runCompilerWith(pyExec, args);
      } else {
        console.error(install.stderr || install.stdout);
        throw new Error(`failed to install PyYAML with ${pyExec} -m pip`);
      }
    }
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    process.exitCode = result.status ?? 1;
    return;
  }
  throw new Error(`python3 not found; install Python 3 from https://www.python.org (${lastError?.message ?? "no candidate worked"})`);
}

async function main() {
  assertNodeVersion();
  const options = parseArguments(process.argv.slice(2));
  if (options.version) {
    printVersion();
    return;
  }
  if (options.help) {
    printHelp(options.command);
    return;
  }

  if (options.command === "install") {
    await installSkill(options);
    return;
  }

  if (options.command === "compile") {
    runCompile(options);
    return;
  }

  const { server, url } = await startEditorServer({ port: options.port });
  let targetUrl = url;
  if (options.project) {
    const cleanProject = options.project.replace(/\\/g, "/");
    targetUrl = `${url}?project=${encodeURIComponent(cleanProject)}`;
    console.log(`\n✓ PPTD 项目直通预览已启动: ${options.project}`);
    console.log(`  预览与导出地址: ${targetUrl}\n`);
    console.log(`已在默认浏览器中打开该文稿，可在页面内查看翻页动效，或在右上角点击「导出」下载本地编译的 PPTX。`);
  } else {
    console.log(`Open Kimi PPT editor is running at ${url}`);
  }
  console.log("Press Ctrl+C to stop the server.");
  if (options.open) openBrowser(targetUrl);

  const shutdown = () => server.close(() => process.exit(0));
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
});
