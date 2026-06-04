const fs = require("fs");
const vm = require("vm");

const source = `${fs.readFileSync("app.js", "utf8")}\n;globalThis.__dict = dictionary;`;
const noop = () => {};

function elementStub() {
  return {
    innerHTML: "",
    textContent: "",
    value: "",
    hidden: false,
    href: "",
    dataset: {},
    style: {},
    classList: { toggle: noop, add: noop, remove: noop },
    addEventListener: noop,
    removeEventListener: noop,
    setAttribute: noop,
    removeAttribute: noop,
    focus: noop,
    scrollIntoView: noop,
    querySelector: () => elementStub(),
    querySelectorAll: () => [],
    appendChild: noop,
  };
}

const sandbox = {
  console,
  window: { addEventListener: noop, open: noop, scrollTo: noop },
  document: {
    addEventListener: noop,
    querySelector: () => elementStub(),
    querySelectorAll: () => [],
    getElementById: () => elementStub(),
    body: elementStub(),
    createElement: () => elementStub(),
  },
  navigator: { clipboard: { writeText: noop } },
  location: {},
  fetch() {
    return Promise.resolve({ ok: false, json: () => ({}) });
  },
  setTimeout,
  clearTimeout,
  requestAnimationFrame: (fn) => fn(),
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { timeout: 15000 });

const dictionary = sandbox.__dict || [];
const badSuffixes = ["核心概念", "工作机制", "组成结构", "关键流程", "常见指标", "设计权衡", "错误模式", "排障方法", "安全边界", "实践场景"];
const allTerms = [];
const nameCounts = new Map();
const explanationCounts = new Map();

for (const section of dictionary) {
  for (const term of section.terms || []) {
    const name = String(term.name || "").trim();
    const explanation = String(term.explanation || "").replace(/\s+/g, " ").trim();
    const image = String(term.image || "").replace(/\s+/g, " ").trim();
    allTerms.push({ ...term, sectionId: section.id, sectionTitle: section.title, name, explanation, image });
    if (name) nameCounts.set(name, (nameCounts.get(name) || 0) + 1);
    if (explanation) explanationCounts.set(explanation, (explanationCounts.get(explanation) || 0) + 1);
  }
}

const names = new Set(allTerms.map((term) => term.name));
const duplicates = [...nameCounts.entries()].filter(([, count]) => count > 1);
const repeatedExplanations = [...explanationCounts.entries()].filter(([, count]) => count > 1);
const lowValueNames = allTerms.filter((term) => badSuffixes.some((suffix) => term.name.endsWith(suffix)));
const missingCoreFields = allTerms.filter((term) => !term.name || !term.tag || !term.explanation || !term.image);
const missingEnglish = allTerms.filter((term) => !String(term.english || "").trim());
const shortExplanations = allTerms.filter((term) => term.explanation.length > 0 && term.explanation.length < 28);
const genericExplanations = allTerms.filter((term) => /只是一个零件|重要名词/.test(term.explanation) && term.explanation.length < 90);
const missingRelations = [];

for (const term of allTerms) {
  for (const related of term.related || []) {
    if (!names.has(related)) {
      missingRelations.push({ term: term.name, related });
    }
  }
}

const bySection = dictionary.map((section) => ({
  id: section.id,
  title: section.title,
  count: (section.terms || []).length,
}));

const report = {
  totalTerms: allTerms.length,
  totalSections: dictionary.length,
  duplicates: duplicates.length,
  duplicateSamples: duplicates.slice(0, 20),
  lowValueNames: lowValueNames.length,
  repeatedExactExplanations: repeatedExplanations.length,
  missingCoreFields: missingCoreFields.length,
  missingEnglish: missingEnglish.length,
  shortExplanations: shortExplanations.length,
  genericShortExplanations: genericExplanations.length,
  missingRelations: missingRelations.length,
  missingRelationSamples: missingRelations.slice(0, 25),
  largestSections: [...bySection].sort((a, b) => b.count - a.count).slice(0, 12),
  smallestSections: [...bySection].sort((a, b) => a.count - b.count).slice(0, 12),
};

console.log(JSON.stringify(report, null, 2));

if (duplicates.length || lowValueNames.length || repeatedExplanations.length || missingCoreFields.length || missingEnglish.length) {
  process.exitCode = 1;
}
