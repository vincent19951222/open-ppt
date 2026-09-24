import { createReadStream, existsSync, readdirSync, readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { spawnSync } from "node:child_process";
import { basename, dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { assertWritableChangePath, extractPagePaths, titleFromManifest } from "../editor/lib.js";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultEditorDirectory = resolve(packageRoot, "editor");

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
]);

const IMAGE_MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

function respond(response, statusCode, message) {
  response.writeHead(statusCode, {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "*",
  });
  response.end(message);
}

export function createEditorServer({ editorDirectory = defaultEditorDirectory } = {}) {
  const root = resolve(editorDirectory);
  const rootPrefix = `${root}${sep}`;

  return createServer((request, response) => {
    let requestUrl;
    try {
      requestUrl = new URL(request.url ?? "/", "http://127.0.0.1");
    } catch {
      respond(response, 400, "Bad Request");
      return;
    }

    const pathname = decodeURIComponent(requestUrl.pathname);

    if (request.method === "OPTIONS") {
      response.writeHead(204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
      });
      response.end();
      return;
    }

    // API endpoint: GET /api/deck?path=<project-path>
    if (pathname === "/api/deck") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        respond(response, 405, "Method Not Allowed");
        return;
      }
      const rawPath = requestUrl.searchParams.get("path");
      if (!rawPath) {
        respond(response, 400, "Missing required 'path' query parameter");
        return;
      }

      const target = resolve(process.cwd(), rawPath);
      if (!existsSync(target)) {
        respond(response, 404, `Project path not found: ${rawPath}`);
        return;
      }

      let projectDir = target;
      let manifestPath;
      if (statSync(target).isFile()) {
        if (!target.endsWith(".pptd")) {
          respond(response, 400, "File must be a .pptd manifest");
          return;
        }
        manifestPath = target;
        projectDir = dirname(target);
      } else {
        const entries = readdirSync(projectDir);
        const pptds = entries.filter((e) => e.endsWith(".pptd"));
        if (pptds.length === 0) {
          respond(response, 404, `No .pptd manifest found in ${rawPath}`);
          return;
        }
        manifestPath = join(projectDir, pptds[0]);
      }

      try {
        const manifestContent = readFileSync(manifestPath, "utf8");
        const title = titleFromManifest(manifestContent, basename(manifestPath, ".pptd"));
        const pagePaths = extractPagePaths(manifestContent);
        const pages = pagePaths.map((pageRel) => {
          const full = join(projectDir, pageRel);
          if (!existsSync(full)) {
            throw new Error(`Page file not found: ${pageRel}`);
          }
          return {
            path: pageRel,
            content: readFileSync(full, "utf8"),
          };
        });

        const imageMap = {};
        const mediaDir = join(projectDir, "media");
        if (existsSync(mediaDir) && statSync(mediaDir).isDirectory()) {
          for (const entry of readdirSync(mediaDir)) {
            const full = join(mediaDir, entry);
            if (statSync(full).isFile()) {
              const ext = extname(entry).toLowerCase();
              const mime = IMAGE_MIME[ext] || "application/octet-stream";
              const dataUrl = `data:${mime};base64,${readFileSync(full).toString("base64")}`;
              imageMap[`media/${entry}`] = dataUrl;
              imageMap[entry] = dataUrl;
            }
          }
        }

        const payload = {
          id: basename(manifestPath, ".pptd"),
          title,
          manifestPath: relative(projectDir, manifestPath).replaceAll("\\", "/"),
          manifestContent,
          projectPath: relative(process.cwd(), projectDir).replaceAll("\\", "/") || ".",
          pages,
          imageMap,
        };

        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store",
        });
        response.end(JSON.stringify(payload));
      } catch (err) {
        respond(response, 500, err.message);
      }
      return;
    }

    // API endpoint: POST /api/save
    if (pathname === "/api/save") {
      if (request.method !== "POST") {
        respond(response, 405, "Method Not Allowed");
        return;
      }
      let body = "";
      request.on("data", (chunk) => {
        body += chunk;
        if (body.length > 25 * 1024 * 1024) {
          request.destroy();
        }
      });
      request.on("end", () => {
        try {
          const data = JSON.parse(body);
          const projectPath = resolve(process.cwd(), data.projectPath || ".");
          const changes = Array.isArray(data.changes) ? data.changes : [];
          for (const change of changes) {
            const safePath = assertWritableChangePath("", change.path);
            const targetFile = resolve(projectPath, safePath);
            if (change.operation === "delete") {
              if (existsSync(targetFile)) unlinkSync(targetFile);
            } else {
              writeFileSync(targetFile, String(change.content ?? ""), "utf8");
            }
          }
          response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
          response.end(JSON.stringify({ ok: true, saved: changes.length }));
        } catch (err) {
          respond(response, 400, err.message);
        }
      });
      return;
    }

    // API endpoint: GET /api/export?path=<project-path>
    if (pathname === "/api/export") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        respond(response, 405, "Method Not Allowed");
        return;
      }
      const rawPath = requestUrl.searchParams.get("path");
      if (!rawPath) {
        respond(response, 400, "Missing required 'path' parameter");
        return;
      }
      const target = resolve(process.cwd(), rawPath);
      let projectDir = target;
      if (existsSync(target) && statSync(target).isFile()) {
        projectDir = dirname(target);
      }
      if (!existsSync(projectDir)) {
        respond(response, 404, `Directory not found: ${rawPath}`);
        return;
      }

      const pptds = readdirSync(projectDir).filter((f) => f.endsWith(".pptd"));
      if (pptds.length === 0) {
        respond(response, 404, "No .pptd found in directory");
        return;
      }
      const baseName = basename(pptds[0], ".pptd");
      const pptxPath = join(projectDir, `${baseName}.pptx`);

      let needsCompile = !existsSync(pptxPath);
      if (!needsCompile) {
        const pptxMtime = statSync(pptxPath).mtimeMs;
        const files = readdirSync(projectDir);
        for (const f of files) {
          if (f.endsWith(".pptd") && statSync(join(projectDir, f)).mtimeMs > pptxMtime) {
            needsCompile = true;
            break;
          }
        }
        const pagesDir = join(projectDir, "pages");
        if (!needsCompile && existsSync(pagesDir)) {
          for (const f of readdirSync(pagesDir)) {
            if (statSync(join(pagesDir, f)).mtimeMs > pptxMtime) {
              needsCompile = true;
              break;
            }
          }
        }
      }

      if (needsCompile) {
        const compilerScript = resolve(packageRoot, "lib", "compile-pptx.py");
        const pyExec = process.platform === "win32" ? "python" : "python3";
        let res = spawnSync(pyExec, [compilerScript, projectDir], { encoding: "utf8" });
        if (res.status !== 0) {
          const altPy = pyExec === "python" ? "python3" : "python";
          res = spawnSync(altPy, [compilerScript, projectDir], { encoding: "utf8" });
          if (res.status !== 0) {
            respond(response, 500, `Compile PPTX failed: ${res.stderr || res.stdout}`);
            return;
          }
        }
      }

      const stats = statSync(pptxPath);
      const relPath = relative(process.cwd(), pptxPath).replaceAll("\\", "/");
      const downloadUrl = `/api/download?path=${encodeURIComponent(relPath)}`;

      response.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": "*",
      });
      response.end(JSON.stringify({
        downloadUrl,
        sizeBytes: stats.size,
        fileName: `${baseName}.pptx`,
      }));
      return;
    }

    // API endpoint: GET /api/download?path=<file-path>
    if (pathname === "/api/download") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        respond(response, 405, "Method Not Allowed");
        return;
      }
      const rawPath = requestUrl.searchParams.get("path");
      if (!rawPath) {
        respond(response, 400, "Missing required 'path' parameter");
        return;
      }
      const target = resolve(process.cwd(), rawPath);
      if (!existsSync(target) || !statSync(target).isFile()) {
        respond(response, 404, "File not found");
        return;
      }
      const fileName = basename(target);
      const stats = statSync(target);
      response.writeHead(200, {
        "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "Content-Disposition": `attachment; filename*=UTF-8''${encodeURIComponent(fileName)}`,
        "Content-Length": stats.size,
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": "*",
      });
      if (request.method === "HEAD") {
        response.end();
        return;
      }
      createReadStream(target).pipe(response);
      return;
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      respond(response, 405, "Method Not Allowed");
      return;
    }

    let filePathName = pathname;
    if (filePathName.endsWith("/")) filePathName += "index.html";
    const filePath = resolve(root, `.${filePathName}`);
    if (filePath !== root && !filePath.startsWith(rootPrefix)) {
      respond(response, 403, "Forbidden");
      return;
    }

    let stats;
    try {
      stats = statSync(filePath);
    } catch {
      respond(response, 404, "Not Found");
      return;
    }

    if (!stats.isFile()) {
      respond(response, 404, "Not Found");
      return;
    }

    response.writeHead(200, {
      "Content-Type": contentTypes.get(extname(filePath).toLowerCase()) ?? "application/octet-stream",
      "Content-Length": stats.size,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });

    if (request.method === "HEAD") {
      response.end();
      return;
    }

    const stream = createReadStream(filePath);
    stream.on("error", () => response.destroy());
    stream.pipe(response);
  });
}

export function startEditorServer({ host = "127.0.0.1", port = 55173 } = {}) {
  const server = createEditorServer();

  return new Promise((resolvePromise, reject) => {
    const onError = (error) => reject(error);
    server.once("error", onError);
    server.listen(port, host, () => {
      server.off("error", onError);
      const address = server.address();
      const actualPort = typeof address === "object" && address ? address.port : port;
      resolvePromise({ server, url: `http://${host}:${actualPort}/` });
    });
  });
}
