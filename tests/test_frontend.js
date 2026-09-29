"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.window = {};
require("../docs/app.js");

const app = global.window.ArchiveApp;

function expectFolder(rel, expected) {
  const name = rel.replace(/\\/g, "/").split("/").pop();
  const result = app.classifyFile(rel, name);
  assert.equal([result.main, result.sub, result.extra_sub].filter(Boolean).join("/"), expected, rel);
}

expectFolder(
  "05 装配文件/接收机/Pick Place for ZC7.820.0017v1.1.csv",
  "03_硬件&结构设计/05_装配文件/坐标文件",
);
expectFolder(
  "05 装配文件/接收机/Pick Place for ZC7.820.0017v1.1.txt",
  "03_硬件&结构设计/05_装配文件/坐标文件",
);
expectFolder("09 文档/共视接收机/北斗卫星共视接收机研制工作总结.pdf", "07_出厂资料");
expectFolder("09 文档/共视接收机/产品合格证.pdf", "07_出厂资料/检验报告");
expectFolder("09 文档/共视接收机/设备测试计划.docx", "07_出厂资料/测试大纲");
expectFolder("08 软件/Tftpd32/debug.log", "04_软件设计/软件程序");
expectFolder("08 软件/Tftpd32/tftpd32.exe", "04_软件设计/软件程序");
expectFolder("08 软件/SNMP监控软件.zip", "04_软件设计/软件程序");

const pending = app.classifyList([{ rel: "杂项/unknown.dat", name: "unknown.dat" }])[0];
assert.equal(pending.status, "待确认");
const outgoing = app.folderOptions().find((option) => option.label === "07_出厂资料");
assert.ok(outgoing, "出厂资料根目录应可在下拉框中选择");
app.applyFolderOverride(pending, outgoing);
assert.equal(pending.folder, "07_出厂资料");
assert.equal(pending.status, "已归档");
assert.equal(pending.reason, "用户手动指定分类");

const page = fs.readFileSync(path.join(__dirname, "..", "docs", "index.html"), "utf8");
assert.match(page, /更新日志 · 2026-09-29/);
assert.match(page, /Pick Place/);

const manifest = app.directoryManifest([
  { folder: "03_硬件&结构设计/05_装配文件/坐标文件", new_name: "Pick Place.csv" },
  { folder: "04_软件设计/软件程序", actual_name: "SNMP监控软件.zip" },
], "共视接收机");
assert.match(manifest, /项目资料归档目录/);
assert.match(manifest, /共视接收机/);
assert.match(manifest, /00_归档目录\.txt/);
assert.match(manifest, /坐标文件\//);
assert.match(manifest, /Pick Place\.csv/);
assert.match(manifest, /SNMP监控软件\.zip/);

console.log("frontend classification tests passed");
