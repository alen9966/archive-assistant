/* 纯浏览器归档：文件不上传，只在同事电脑上分类复制。 */
(function () {
  const UNKNOWN = "99_待确认与其他";
  const MEDIA_STAGES = ["电装完", "三防前", "三防后", "发货前", "包装箱"];
  const SKIP_DIRS = new Set(["history", "__previews", ".git", "__pycache__", ".svn"]);
  const SKIP_FILES = /^(thumbs\.db|desktop\.ini|\.ds_store)$/i;
  const KEEP_NAME = new Set(["坐标文件", "Gerber", "钢网", "库", "工程输出存档", "导出表格", "检查报告"]);

  const SPECS = [
    ["00_需求确认", "技术要求", "硬件/质量"],
    ["00_需求确认", "设计相关资料", "硬件"],
    ["01_任务书", "生产开发计划", "硬件"],
    ["02_方案设计", "硬件方案", "硬件"],
    ["03_硬件&结构设计", "01_原理图", "硬件"],
    ["03_硬件&结构设计", "02_采购清单", "硬件"],
    ["03_硬件&结构设计", "03_PCB", "硬件"],
    ["03_硬件&结构设计", "04_结构图纸", "王杰"],
    ["03_硬件&结构设计", "05_装配文件", "硬件"],
    ["03_硬件&结构设计", "06_整机接线图", "硬件"],
    ["03_硬件&结构设计", "07_领料单", "硬件"],
    ["03_硬件&结构设计", "08_三防图", "硬件"],
    ["04_软件设计", "软件程序", "测试/软件"],
    ["05_生产调试", "00_质量跟踪卡", "质量"],
    ["05_生产调试", "01_元器件采购&检验", "质量/测试"],
    ["05_生产调试", "02_印制板外协&检验", "质量"],
    ["05_生产调试", "03_结构外协&检验", "质量"],
    ["05_生产调试", "04_物料齐套缺件表", "采购"],
    ["05_生产调试", "05_印制板装配外协&检验", "硬件"],
    ["05_生产调试", "06_三防外协&检验", "质量"],
    ["05_生产调试", "07_整机装配&检验", "硬件/生产/质量"],
    ["05_生产调试", "08_调试&自测记录", "硬件/质量"],
    ["06_成品检验", "测试记录", "测试"],
    ["06_成品检验", "试验报告", "测试/质量"],
    ["07_出厂资料", "检验报告", "测试"],
    ["07_出厂资料", "产品说明书", "测试"],
    ["07_出厂资料", "设备及板卡类说明书相关图片存档", "测试/质量"],
    ["07_出厂资料", "测试大纲", "测试"],
    ["07_出厂资料", "测试相关协议", "测试"],
    ["07_出厂资料", "发货记录", "质量"],
    ["07_出厂资料", "多媒体记录", "质量"],
    ["08_项目总结", "项目总结会议纪要", "质量"],
    ["09_售后", "产品配置参数记录", "质量/测试"],
    ["09_售后", "维修单", "质量"],
    ["09_售后", "维修后测试记录", "测试"],
  ];
  const EXTRAS = {
    "05_装配文件": ["装配清单", "阻容表", "装配图", "坐标文件", "钢网"],
    "03_PCB": ["Gerber", "库", "检查报告", "工程输出存档", "导出表格"],
    "01_原理图": ["库", "检查报告"],
    "多媒体记录": MEDIA_STAGES.concat(["待确认"]),
  };

  const RULES = [
    ["09_售后", "维修单", "", ["维修单"], 90],
    ["09_售后", "维修后测试记录", "", ["维修后测试记录", "维修后测试"], 90],
    ["09_售后", "产品配置参数记录", "", ["配置参数记录", "配置参数"], 80],
    ["08_项目总结", "项目总结会议纪要", "", ["会议纪要", "项目总结"], 85],
    ["07_出厂资料", "发货记录", "", ["发货单", "发货记录", "checklist"], 80],
    ["07_出厂资料", "测试相关协议", "", ["相关协议", "测试协议"], 75],
    ["07_出厂资料", "测试大纲", "", ["测试大纲"], 85],
    ["07_出厂资料", "检验报告", "", ["检验报告"], 80],
    ["07_出厂资料", "产品说明书", "", ["产品说明书", "产品手册"], 80],
    ["07_出厂资料", "设备及板卡类说明书相关图片存档", "", ["实物图", "web图", "界面图"], 80],
    ["07_出厂资料", "多媒体记录", "", ["多媒体记录", "电装完", "三防前", "三防后", "发货前"], 70],
    ["06_成品检验", "试验报告", "", ["高低温工作试验报告", "高低温", "环境试验报告", "环境试验"], 85],
    ["06_成品检验", "测试记录", "", ["常规测试记录表", "常规测试", "成品测试记录"], 80],
    ["05_生产调试", "08_调试&自测记录", "", ["调试记录表", "调试记录", "自测记录"], 85],
    ["05_生产调试", "07_整机装配&检验", "", ["整机装配记录表", "整机装配记录"], 90],
    ["05_生产调试", "05_印制板装配外协&检验", "", ["单板测试记录表", "单板测试记录", "单板测试", "电装检验"], 88],
    ["05_生产调试", "01_元器件采购&检验", "", ["关重件", "元器件检验", "元器件采购"], 80],
    ["05_生产调试", "00_质量跟踪卡", "", ["质量跟踪卡", "履历表"], 90],
    ["05_生产调试", "03_结构外协&检验", "", ["结构件入厂", "质量问题反馈单", "结构外协"], 80],
    ["05_生产调试", "04_物料齐套缺件表", "", ["缺件表", "齐套"], 80],
    ["05_生产调试", "02_印制板外协&检验", "", ["印制板外协", "丝印"], 70],
    ["05_生产调试", "06_三防外协&检验", "", ["三防外协"], 80],
    ["03_硬件&结构设计", "07_领料单", "", ["领料单"], 95],
    ["03_硬件&结构设计", "02_采购清单", "", ["采购清单", "bom表", "物料清单", "bom"], 92],
    ["03_硬件&结构设计", "08_三防图", "", ["三防图", "三防图纸"], 95],
    ["03_硬件&结构设计", "06_整机接线图", "", ["整机接线图", "接线图", "接线表"], 85],
    ["03_硬件&结构设计", "05_装配文件", "阻容表", ["外协阻容备料", "外协阻容清单", "阻容备料清单", "阻容备料", "阻容清单", "阻容表"], 94],
    ["03_硬件&结构设计", "05_装配文件", "装配清单", ["装配清单"], 92],
    ["03_硬件&结构设计", "05_装配文件", "装配图", ["装配图"], 92],
    ["03_硬件&结构设计", "05_装配文件", "坐标文件", ["坐标文件夹", "坐标文件", "pickup", "centroid"], 92],
    ["03_硬件&结构设计", "05_装配文件", "钢网", ["钢网"], 90],
    ["03_硬件&结构设计", "04_结构图纸", "", ["结构图纸", "结构图", "三维", "二维", "结构清单"], 75],
    ["03_硬件&结构设计", "01_原理图", "", ["原理图", "schdoc", "schematic prints", "schematic"], 90],
    ["03_硬件&结构设计", "03_PCB", "Gerber", ["gerber", "光绘"], 90],
    ["03_硬件&结构设计", "03_PCB", "", ["pcbdoc"], 85],
    ["04_软件设计", "软件程序", "", ["固件", "boot_", "软件程序", "下载程序", "网络升级"], 80],
    ["02_方案设计", "硬件方案", "", ["硬件方案", "方案设计"], 80],
    ["01_任务书", "生产开发计划", "", ["生产开发计划", "任务书"], 85],
    ["00_需求确认", "设计相关资料", "", ["规格书", "铷钟"], 70],
    ["00_需求确认", "技术要求", "", ["技术要求", "需求规格"], 75],
  ];
  const FOLDER_HINTS = [
    [["外协阻容备料", "外协阻容清单", "阻容备料", "阻容清单", "阻容表", "阻容"], "03_硬件&结构设计", "05_装配文件", "阻容表", "阻容表", 94],
    [["lib", "library"], "03_硬件&结构设计", "01_原理图", "库", "库", 93],
    [["坐标文件夹", "坐标文件", "坐标", "pickup", "centroid", "xy"], "03_硬件&结构设计", "05_装配文件", "坐标文件", "坐标文件", 93],
    [["装配清单"], "03_硬件&结构设计", "05_装配文件", "装配清单", "装配清单", 93],
    [["装配图"], "03_硬件&结构设计", "05_装配文件", "装配图", "装配图", 93],
    [["钢网", "钢网文件"], "03_硬件&结构设计", "05_装配文件", "钢网", "钢网文件", 92],
    [["gerber", "gerbers", "光绘"], "03_硬件&结构设计", "03_PCB", "Gerber", "Gerber", 93],
    [["原理图", "schematic", "schematic prints", "sch"], "03_硬件&结构设计", "01_原理图", "", "原理图", 93],
    [["采购清单", "bom表", "物料清单", "bom"], "03_硬件&结构设计", "02_采购清单", "", "采购清单", 94],
    [["单板测试记录表", "单板测试记录", "单板测试"], "05_生产调试", "05_印制板装配外协&检验", "", "单板测试记录表", 93],
    [["三防图", "三防图纸"], "03_硬件&结构设计", "08_三防图", "", "三防图", 95],
    [["pcb", "pcb图", "印制板"], "03_硬件&结构设计", "03_PCB", "", "PCB", 90],
  ];

  const PCB_EXTS = new Set([".pcbdoc", ".pcb", ".prjpcb", ".pcbdwf", ".gbr", ".gerber", ".gtl", ".gbl", ".gto", ".gts", ".gbs", ".gbo", ".gm1", ".gd1", ".gg1", ".drl", ".art"]);
  const SCH_EXTS = new Set([".schdoc", ".sch", ".schdot"]);
  const LIB_SCH = new Set([".schlib", ".intlib"]);
  const LIB_PCB = new Set([".pcblib"]);
  const FW_EXTS = new Set([".bin", ".hex", ".axf", ".elf", ".out"]);
  const MEDIA_EXTS = new Set([".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".heic", ".mp4", ".mov", ".avi", ".mkv", ".wmv"]);
  const ARCHIVE_EXTS = new Set([".rar", ".zip", ".7z"]);
  const TABLE_EXTS = new Set([".xlsx", ".xls", ".csv"]);
  const COAT_EXTS = new Set([".pdf", ".dwg", ".dxf", ".png", ".jpg", ".jpeg"]);
  const BOARD_STEM = /^Z?C\d+[._]\d+[._]\d+(?:[-_]V[\d.]+)?$/i;

  function folderOptions() {
    const opts = [];
    for (const [main, sub, owners] of SPECS) {
      const label = main + "/" + sub;
      opts.push({ main, sub, extra_sub: "", label, owners });
      for (const extra of EXTRAS[sub] || []) {
        opts.push({ main, sub, extra_sub: extra, label: label + "/" + extra, owners });
      }
    }
    opts.push({ main: UNKNOWN, sub: "", extra_sub: "", label: UNKNOWN, owners: "" });
    return opts;
  }

  function treePaths() {
    const paths = [];
    const seen = new Set();
    const add = (p) => { if (p && !seen.has(p)) { seen.add(p); paths.push(p); } };
    for (const [main, sub] of SPECS) {
      add(main);
      add(main + "/" + sub);
      for (const extra of EXTRAS[sub] || []) add(main + "/" + sub + "/" + extra);
    }
    add(UNKNOWN);
    return paths;
  }

  function extOf(name) {
    const i = name.lastIndexOf(".");
    return i < 0 ? "" : name.slice(i).toLowerCase();
  }
  function stemOf(name) {
    const i = name.lastIndexOf(".");
    return i < 0 ? name : name.slice(0, i);
  }
  function norm(s) { return String(s || "").replace(/\\/g, "/").toLowerCase(); }
  function skipDir(name) {
    const n = name.toLowerCase();
    return SKIP_DIRS.has(n) || n.startsWith("project logs");
  }
  function looksBom(text) {
    const hay = norm(text);
    if (["采购清单", "bom表", "物料清单"].some((m) => hay.includes(m))) return true;
    return /(^|[/_\\s.-])bom($|[/_\\s.-]|表)/.test(hay);
  }
  function inSch(rel) {
    const p = norm(rel);
    return p.includes("原理图") || p.includes("/sch/") || p.startsWith("sch/") || p.includes("/schlib/");
  }

  function fromSpecial(rel, name) {
    const ext = extOf(name);
    const hay = norm(rel + " " + name);
    const stem = stemOf(name);
    if (LIB_SCH.has(ext)) return { main: "03_硬件&结构设计", sub: "01_原理图", extra_sub: "库", confidence: 95, reason: ext === ".intlib" ? ".IntLib 为原理图与PCB共用集成库" : "原理图库", file_type: "库", pending: false };
    if (LIB_PCB.has(ext)) return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: "库", confidence: 95, reason: "PCB 封装库", file_type: "库", pending: false };
    if (ext === ".pcbdwf") return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: "", confidence: 94, reason: "PCBDwf 为 PCB 文件", file_type: "PCB", pending: false };
    if (ARCHIVE_EXTS.has(ext) && hay.includes("project outputs")) return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: "工程输出存档", confidence: 94, reason: "Project Outputs 压缩包为工程输出存档", file_type: "工程输出存档", pending: false };
    if (hay.includes("design rule check") || name.includes("设计规则检查")) {
      if (inSch(rel) || hay.includes("electrical")) return { main: "03_硬件&结构设计", sub: "01_原理图", extra_sub: "检查报告", confidence: 93, reason: "原理图规则检查", file_type: "检查报告", pending: false };
      return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: "检查报告", confidence: 93, reason: "PCB Design Rule Check", file_type: "检查报告", pending: false };
    }
    if (hay.includes("electrical rule") || name.includes("电气规则检查")) return { main: "03_硬件&结构设计", sub: "01_原理图", extra_sub: "检查报告", confidence: 93, reason: "原理图电气规则检查", file_type: "检查报告", pending: false };
    if (COAT_EXTS.has(ext) && !["三防前", "三防后", "三防外协"].some((x) => name.includes(x))) {
      if (stem === "三防" || stem === "三防图" || stem.endsWith("_三防") || stem.endsWith("-三防") || stem.endsWith("三防图")) {
        return { main: "03_硬件&结构设计", sub: "08_三防图", extra_sub: "", confidence: 96, reason: "三防图", file_type: "三防图", pending: false };
      }
    }
    if (TABLE_EXTS.has(ext) && BOARD_STEM.test(stem)) return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: "导出表格", confidence: 88, reason: "板号同名导出表格", file_type: "导出表格", pending: false };
    return null;
  }

  function fromFolder(rel) {
    const parts = rel.replace(/\\/g, "/").split("/").filter(Boolean);
    if (parts.length <= 1) return null;
    const folders = parts.slice(0, -1);
    let best = null, bestDepth = -1;
    folders.forEach((raw, depth) => {
      const part = norm(raw);
      for (const [aliases, main, sub, extra, ftype, conf] of FOLDER_HINTS) {
        const hit = aliases.slice().sort((a, b) => b.length - a.length).find((alias) => {
          const a = alias.toLowerCase();
          const matched = a.length <= 3 && /^[a-z0-9]+$/.test(a) ? (part === a || part === a + "s") : (part === a || part.includes(a));
          if (!matched) return false;
          if (a === "pcb" && looksBom(raw)) return false;
          return true;
        });
        if (!hit) continue;
        if (depth >= bestDepth && (!best || conf >= best.confidence)) {
          best = { main, sub, extra_sub: extra, confidence: conf, reason: "源文件夹「" + raw + "」", file_type: ftype, pending: false };
          bestDepth = depth;
        }
      }
    });
    return best;
  }

  function fromKeywords(rel, name) {
    const hay = norm(rel + " " + name);
    let best = null;
    for (const [main, sub, extra, kws, weight] of RULES) {
      const kw = kws.find((k) => hay.includes(k.toLowerCase()));
      if (!kw) continue;
      const cand = { main, sub, extra_sub: extra, confidence: weight, reason: "关键词「" + kw + "」", file_type: extra || sub, pending: weight < 60 };
      if (!best || cand.confidence > best.confidence) best = cand;
    }
    return best;
  }

  function fromExt(rel, name) {
    const ext = extOf(name);
    const hay = norm(rel + " " + name);
    if (SCH_EXTS.has(ext) || name.includes("原理图")) return { main: "03_硬件&结构设计", sub: "01_原理图", extra_sub: "", confidence: 92, reason: "原理图扩展名", file_type: "原理图", pending: false };
    if (looksBom(name)) return null;
    if (PCB_EXTS.has(ext)) {
      const gerber = ![".pcbdoc", ".pcb", ".prjpcb", ".pcbdwf"].includes(ext);
      return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: gerber ? "Gerber" : "", confidence: 90, reason: "PCB/Gerber 扩展名", file_type: gerber ? "Gerber" : "PCB", pending: false };
    }
    if (/(^|[/_\\s.-])pcb($|[/_\\s.-])/.test(hay) && !name.includes("采购") && !looksBom(hay)) {
      return { main: "03_硬件&结构设计", sub: "03_PCB", extra_sub: "", confidence: 86, reason: "路径或文件名含 PCB", file_type: "PCB", pending: false };
    }
    if (FW_EXTS.has(ext) || name.toUpperCase().startsWith("BOOT_") || name.includes("固件")) {
      return { main: "04_软件设计", sub: "软件程序", extra_sub: "", confidence: 88, reason: "固件/BOOT", file_type: "软件程序", pending: false };
    }
    return null;
  }

  function classifyFile(rel, name) {
    const special = fromSpecial(rel, name);
    const folder = fromFolder(rel);
    const named = fromKeywords(rel, name);
    const exted = fromExt(rel, name);
    let best = null;
    for (const cand of [special, folder, named, exted]) {
      if (!cand) continue;
      if (!best || cand.confidence > best.confidence) best = cand;
      else if (cand.confidence === best.confidence && cand === named && folder) best = cand;
    }
    const ext = extOf(name);
    const hay = norm(rel + " " + name);
    let stage = "";
    for (const s of MEDIA_STAGES) if (hay.includes(s) || name.includes(s)) { stage = s; break; }
    if (stage && MEDIA_EXTS.has(ext)) {
      best = { main: "07_出厂资料", sub: "多媒体记录", extra_sub: stage, confidence: Math.max(best ? best.confidence : 0, 80), reason: "多媒体阶段「" + stage + "」", file_type: "多媒体记录_" + stage, pending: false };
    } else if (best && best.sub === "多媒体记录") {
      const extra = stage || "待确认";
      best = { ...best, extra_sub: extra, pending: extra === "待确认" };
    } else if (MEDIA_EXTS.has(ext) && (!best || best.confidence < 70)) {
      best = { main: "07_出厂资料", sub: "多媒体记录", extra_sub: stage || "待确认", confidence: 45, reason: "图片/视频扩展名，阶段未识别", file_type: "多媒体记录", pending: true };
    }
    if (!best || best.confidence < 55) {
      return { main: UNKNOWN, sub: "", extra_sub: "", confidence: best ? best.confidence : 0, reason: best ? "置信度低：" + best.reason : "无法可靠分类", file_type: "待确认", pending: true };
    }
    return best;
  }

  function destFolder(cls) {
    if (cls.main === UNKNOWN || !cls.main) return UNKNOWN;
    return [cls.main, cls.sub, cls.extra_sub].filter(Boolean).join("/");
  }

  function ownerOf(cls) {
    const spec = SPECS.find((s) => s[0] === cls.main && s[1] === cls.sub);
    return spec ? spec[2] : "";
  }

  function classifyList(items) {
    return items.map((it) => {
      const cls = classifyFile(it.rel, it.name);
      const folder = destFolder(cls);
      const keep = KEEP_NAME.has(cls.extra_sub) || cls.main === UNKNOWN;
      return {
        id: it.rel,
        rel: it.rel,
        original_name: it.name,
        new_name: keep ? it.name : it.name,
        main: cls.main,
        sub: cls.sub,
        extra_sub: cls.extra_sub,
        folder,
        owner: ownerOf(cls),
        status: cls.pending || cls.main === UNKNOWN ? "待确认" : "已归档",
        confidence: cls.confidence,
        reason: cls.reason,
        file: it.file,
        handle: it.handle || null,
      };
    });
  }

  async function walkHandle(dirHandle, prefix, acc) {
    for await (const [name, handle] of dirHandle.entries()) {
      if (handle.kind === "directory") {
        if (skipDir(name)) continue;
        await walkHandle(handle, prefix + name + "/", acc);
      } else {
        if (SKIP_FILES.test(name) || name.startsWith("~$")) continue;
        if (prefix.split("/").filter(Boolean).some(skipDir)) continue;
        const file = await handle.getFile();
        acc.push({ file, rel: prefix + name, name, handle });
      }
    }
  }

  function fromFileList(fileList) {
    const acc = [];
    for (const file of fileList) {
      const rel = (file.webkitRelativePath || file.relativePath || file.name).replace(/\\/g, "/");
      const parts = rel.split("/");
      if (parts.some(skipDir) || SKIP_FILES.test(file.name) || file.name.startsWith("~$")) continue;
      acc.push({ file, rel, name: file.name, handle: null });
    }
    return acc;
  }

  async function ensureDir(root, parts) {
    let dir = root;
    for (const p of parts) {
      if (!p) continue;
      dir = await dir.getDirectoryHandle(p, { create: true });
    }
    return dir;
  }

  async function fileExists(dir, name) {
    try { await dir.getFileHandle(name); return true; } catch { return false; }
  }

  async function uniqueName(dir, name) {
    if (!(await fileExists(dir, name))) return name;
    const i = name.lastIndexOf(".");
    const stem = i < 0 ? name : name.slice(0, i);
    const ext = i < 0 ? "" : name.slice(i);
    for (const suf of ["_重复1", "_重复2", "_v2"]) {
      const n = stem + suf + ext;
      if (!(await fileExists(dir, n))) return n;
    }
    let n = 3;
    while (await fileExists(dir, stem + "_重复" + n + ext)) n += 1;
    return stem + "_重复" + n + ext;
  }

  async function writeTree(root) {
    for (const p of treePaths()) await ensureDir(root, p.split("/"));
  }

  async function copyOut(root, files) {
    let copied = 0;
    for (const f of files) {
      const parts = f.folder.split("/");
      const dir = await ensureDir(root, parts);
      const name = await uniqueName(dir, f.new_name || f.original_name);
      const dest = await dir.getFileHandle(name, { create: true });
      const w = await dest.createWritable();
      const blob = f.file;
      await w.write(blob);
      await w.close();
      copied += 1;
    }
    return copied;
  }

  function crc32(buf) {
    let c = ~0;
    const t = crc32.t || (crc32.t = (function () {
      const a = new Uint32Array(256);
      for (let n = 0; n < 256; n++) {
        let k = n;
        for (let i = 0; i < 8; i++) k = k & 1 ? 0xedb88320 ^ (k >>> 1) : k >>> 1;
        a[n] = k;
      }
      return a;
    })());
    const u = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
    for (let i = 0; i < u.length; i++) c = t[(c ^ u[i]) & 255] ^ (c >>> 8);
    return ~c >>> 0;
  }

  function u32(n) { const b = new Uint8Array(4); new DataView(b.buffer).setUint32(0, n, true); return b; }
  function u16(n) { const b = new Uint8Array(2); new DataView(b.buffer).setUint16(0, n, true); return b; }

  async function downloadZip(files, zipName) {
    const chunks = [];
    const centrals = [];
    let offset = 0;
    const add = (arr) => { chunks.push(arr); offset += arr.length; };
    for (const f of files) {
      const path = (f.folder + "/" + (f.new_name || f.original_name)).replace(/^\/+/, "");
      const nameBytes = new TextEncoder().encode(path);
      const data = new Uint8Array(await f.file.arrayBuffer());
      const crc = crc32(data);
      const local = new Uint8Array([
        ...[0x50, 0x4b, 0x03, 0x04], ...u16(20), ...u16(0x800), ...u16(0),
        ...u16(0), ...u16(0), ...u32(crc), ...u32(data.length), ...u32(data.length),
        ...u16(nameBytes.length), ...u16(0),
      ]);
      const localOff = offset;
      add(local); add(nameBytes); add(data);
      const central = new Uint8Array([
        ...[0x50, 0x4b, 0x01, 0x02], ...u16(20), ...u16(20), ...u16(0x800), ...u16(0),
        ...u16(0), ...u16(0), ...u32(crc), ...u32(data.length), ...u32(data.length),
        ...u16(nameBytes.length), ...u16(0), ...u16(0), ...u16(0), ...u16(0), ...u32(0),
        ...u32(localOff),
      ]);
      centrals.push({ central, nameBytes });
    }
    const centralStart = offset;
    for (const c of centrals) { add(c.central); add(c.nameBytes); }
    const end = new Uint8Array([
      ...[0x50, 0x4b, 0x05, 0x06], ...u16(0), ...u16(0),
      ...u16(files.length), ...u16(files.length),
      ...u32(offset - centralStart), ...u32(centralStart), ...u16(0),
    ]);
    add(end);
    const blob = new Blob(chunks, { type: "application/zip" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = zipName || "项目归档包.zip";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  window.ArchiveApp = {
    UNKNOWN,
    folderOptions,
    treePaths,
    classifyFile,
    classifyList,
    walkHandle,
    fromFileList,
    writeTree,
    copyOut,
    downloadZip,
    skipDir,
  };
})();
