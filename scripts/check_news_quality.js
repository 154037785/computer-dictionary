const fs = require("fs");

function loadJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function textLength(text) {
  return String(text || "").replace(/\s+/g, "").length;
}

function hasMojibake(text) {
  return /[鈥�ÃÂâ]{1,}|æ[^\s]{1,}|ç[^\s]{1,}|鍥|绉|妯|鏂|瀹/.test(String(text || ""));
}

function checkFrontier() {
  const data = loadJson("data/frontier-news.json");
  const items = data.items || [];
  const urls = new Set();
  const issues = [];
  const forbiddenTitle = /(消息[：:]|新动态|^国际.{0,16}消息|^外媒.{0,16}消息)/;
  const forbiddenSummary = /(这条新闻主要涉及|报道重点|建议继续关注|出现AI 模型或智能体能力进展|主要影响方向为|这条消息需要放在)/;

  if (items.length < 12) {
    issues.push(`frontier-news has too few items: ${items.length}`);
  }

  for (const item of items) {
    const title = item.titleZh || item.title || "";
    const summary = item.summary || "";
    const url = item.url || "";
    if (!title || textLength(title) < 6) issues.push(`bad title: ${url}`);
    if (forbiddenTitle.test(title)) issues.push(`template title: ${title}`);
    if (textLength(summary) < 200) issues.push(`short summary ${textLength(summary)}: ${title}`);
    if (forbiddenSummary.test(summary)) issues.push(`template summary: ${title}`);
    if (hasMojibake(title) || hasMojibake(summary)) issues.push(`mojibake text: ${title}`);
    if (url) {
      if (urls.has(url)) issues.push(`duplicate url: ${url}`);
      urls.add(url);
    }
  }
  return { count: items.length, issues };
}

const frontier = checkFrontier();
console.log(JSON.stringify({ frontier }, null, 2));
if (frontier.issues.length) {
  process.exitCode = 1;
}
