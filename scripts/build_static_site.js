const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const out = path.join(root, "public");

const copyFiles = [
  "index.html",
  "app.js",
  "styles.css",
  "_headers",
];

const copyDirs = [
  "assets",
];

const dataFiles = [
  "frontier-news.json",
  "wechat-news.json",
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyFile(relativePath) {
  const source = path.join(root, relativePath);
  const target = path.join(out, relativePath);
  ensureDir(path.dirname(target));
  fs.copyFileSync(source, target);
}

function copyDir(relativePath) {
  const source = path.join(root, relativePath);
  const target = path.join(out, relativePath);
  if (!fs.existsSync(source)) return;
  fs.rmSync(target, { recursive: true, force: true });
  fs.cpSync(source, target, { recursive: true });
}

ensureDir(out);
for (const file of copyFiles) copyFile(file);
for (const dir of copyDirs) copyDir(dir);
fs.rmSync(path.join(out, "data"), { recursive: true, force: true });
ensureDir(path.join(out, "data"));
for (const file of dataFiles) copyFile(path.join("data", file));

console.log(`Built static site into ${out}`);
