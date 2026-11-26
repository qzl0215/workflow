#!/usr/bin/env node
// workflow 数据图工具：ECharts + templates/chart-theme.json。
//   node render_chart.mjs png <option.json|--example 名称> --out 图.png [--mode light|dark] [--width 640] [--height 340]
//   node render_chart.mjs page            输出网页用的主题脚本（注册 workflow-light / workflow-dark，提供 WORKFLOW_CHART.fill）
//   node render_chart.mjs examples        列出内置示例
// 依赖首次运行时装进 WORKFLOW_CHART_HOME（默认 ~/.cache/workflow-chart），版本锁定。
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { homedir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ECHARTS_VERSION = "5.6.0";
const DEPS = [`echarts@${ECHARTS_VERSION}`, "@resvg/resvg-js@2.6.2"];
const here = dirname(fileURLToPath(import.meta.url));
const readJson = (path) => JSON.parse(readFileSync(path, "utf8"));
const theme = readJson(join(here, "..", "templates", "chart-theme.json"));

function fail(message) {
  console.error(`render_chart: ${message}`);
  process.exit(2);
}

function fill(value, mode) {
  const tokens = { ...theme.tokens[mode], font: theme.font };
  const walk = (v) => {
    if (typeof v === "string" && v.startsWith("$")) {
      if (!(v.slice(1) in tokens)) fail(`未知颜色变量 ${v}；只能用 chart-theme.json 里的：${Object.keys(tokens).join(", ")}`);
      return tokens[v.slice(1)];
    }
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, walk(x)]));
    return v;
  };
  return walk(value);
}

function loadDeps() {
  const home = process.env.WORKFLOW_CHART_HOME || join(homedir(), ".cache", "workflow-chart");
  const require = createRequire(join(home, "package.json"));
  try {
    if (require("echarts/package.json").version !== ECHARTS_VERSION) throw new Error("version");
    require.resolve("@resvg/resvg-js");
  } catch {
    console.error(`render_chart: 首次使用，安装 ${DEPS.join(" ")} 到 ${home}`);
    mkdirSync(home, { recursive: true });
    if (!existsSync(join(home, "package.json"))) writeFileSync(join(home, "package.json"), '{"private":true}\n');
    try {
      execFileSync("npm", ["install", "--prefix", home, "--no-audit", "--no-fund", "--loglevel=error", ...DEPS], { stdio: "inherit" });
    } catch {
      fail("npm 安装失败；需要 Node 18+ 和可访问的 npm 源");
    }
  }
  return { echarts: require("echarts"), Resvg: require("@resvg/resvg-js").Resvg };
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith("--")) args[argv[i].slice(2)] = argv[i + 1]?.startsWith("--") ? true : argv[++i];
    else args._.push(argv[i]);
  }
  return args;
}

function png(args) {
  const examples = readJson(join(here, "..", "templates", "chart-examples.json"));
  let spec;
  if (args.example) {
    spec = examples[args.example];
    if (!spec) fail(`没有示例 ${args.example}；可用：${Object.keys(examples).join(", ")}`);
  } else if (args._[1]) {
    const raw = readJson(args._[1]);
    spec = raw.option ? raw : { option: raw };
  } else fail("缺少图表配置文件或 --example");
  if (!args.out) fail("缺少 --out");
  const mode = args.mode || "light";
  if (!theme.tokens[mode]) fail("--mode 只能是 light 或 dark");
  const width = Number(args.width || spec.width || 640);
  const height = Number(args.height || spec.height || 340);

  const { echarts, Resvg } = loadDeps();
  echarts.registerTheme(`workflow-${mode}`, fill(theme.echarts, mode));
  const chart = echarts.init(null, `workflow-${mode}`, { renderer: "svg", ssr: true, width, height });
  chart.setOption({ ...fill(spec.option, mode), animation: false });
  const svg = chart.renderToSVGString();
  chart.dispose();
  const font = { loadSystemFonts: true, defaultFontFamily: theme.font.split(",")[0].trim() };
  writeFileSync(args.out, new Resvg(svg, { fitTo: { mode: "zoom", value: 2 }, font }).render().asPng());
  console.log(`render_chart: ${args.out}（${width}×${height}，${mode}）`);
}

function page() {
  const themes = { light: fill(theme.echarts, "light"), dark: fill(theme.echarts, "dark") };
  const tokens = Object.fromEntries(Object.keys(theme.tokens).map((m) => [m, { ...theme.tokens[m], font: theme.font }]));
  process.stdout.write(`// workflow 数据图主题，由 scripts/render_chart.mjs page 生成；先加载 echarts@${ECHARTS_VERSION}
window.WORKFLOW_CHART = (function () {
  var tokens = ${JSON.stringify(tokens)};
  var themes = ${JSON.stringify(themes)};
  Object.keys(themes).forEach(function (m) { echarts.registerTheme("workflow-" + m, themes[m]); });
  function fill(v, mode) {
    if (typeof v === "string" && v.charAt(0) === "$") {
      if (!(v.slice(1) in tokens[mode])) throw new Error("未知颜色变量 " + v);
      return tokens[mode][v.slice(1)];
    }
    if (Array.isArray(v)) return v.map(function (x) { return fill(x, mode); });
    if (v && typeof v === "object") { var o = {}; for (var k in v) o[k] = fill(v[k], mode); return o; }
    return v;
  }
  return { tokens: tokens, fill: fill, theme: function (mode) { return "workflow-" + mode; }, echartsVersion: "${ECHARTS_VERSION}" };
})();
`);
}

const args = parseArgs(process.argv.slice(2));
const command = args._[0];
if (command === "png") png(args);
else if (command === "page") page();
else if (command === "examples") {
  const examples = readJson(join(here, "..", "templates", "chart-examples.json"));
  for (const [name, e] of Object.entries(examples)) console.log(`${name}\t${e.use}`);
} else fail("用法：png <option.json|--example 名称> --out 图.png [--mode light|dark] | page | examples");
