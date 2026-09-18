---
name: archive-assistant
description: >-
  Runs the local project archive assistant (plan/apply), classifies hardware
  production files into the template folder tree, and generates index/missing/
  pending/duplicate reports. Use when the user asks to archive project files,
  归档, 资料归档, classify documents, or generate 归档索引/归档报告.
---

# 项目资料归档助手

用仓库里的程序执行归档，不要手抄文件充数。政策空白用「暂定默认，可改」；项目实例字段不编造。

## 运行

工作区根目录：

```text
py -3 -m archive_assistant web
py -3 -m archive_assistant plan --source <待归档目录> --output <归档输出目录> --config project.yaml
py -3 -m archive_assistant apply --source <待归档目录> --output <归档输出目录> --config project.yaml
```

- `web`：本地网页，把整个资料文件夹拖入后自动分类，点「生成分类文件夹」才复制。认不出的进 99。
- `plan`：建目录、出五件套，不复制资料。
- `apply`：复制（默认）。`--zip` 才打包。
- 移动：配置 `allow_move: true` 且 `--confirm-move`。否则只复制。
- 配置从 `project.example.yaml` 复制；只填已知项。

## 必须遵守

1. 目录名与 `archive_assistant/catalog.py` 一致，不改主文件夹序号。
2. 无法分类 → `99_待确认与其他/`，写明原因。
3. 同名不覆盖；重复用 sha256；敏感只标记不外传。
4. 矩阵 12 类缺失才标「缺失」；其它模板项标「待确认是否必交」。
5. 输出 `00_归档索引`、`00_缺失资料清单`、`00_待确认清单`、`00_重复文件清单`、`00_归档报告.md`。
6. 改代码后执行：`py -3 -m unittest tests.test_archive tests.test_classify tests.test_web -v`。

详细命名与必查项以项目规则 `.cursor/rules/archive-assistant.mdc` 为准。
