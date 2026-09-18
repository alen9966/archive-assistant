# 项目资料归档助手

在本目录打开终端。未装依赖时：`py -3 -m pip install -r requirements.txt`（xlsx 写失败仍会出 csv）。

## 网页（推荐）

```text
py -3 -m archive_assistant web
```

浏览器打开 `http://127.0.0.1:8765/`。大文件夹请点「选择本机文件夹」（或把路径填到左侧），不要用浏览器上传。几百 MB 的 Altium 工程走本机目录扫描；识别后再点「生成分类文件夹」才复制，不删原文件。Altium 的 `History` / `__Previews` / `Project Logs` 默认跳过。`--no-browser` 可不自动打开。

本工具在本地处理图纸和生产资料，**不会把文件发到公网**。GitHub 上可以在线查看代码和说明。

## 配置

复制 `project.example.yaml` 为 `project.yaml`，只填已知字段，不要编造。网页会预填。

## 命令行（仍可用）

```text
py -3 -m archive_assistant plan --source 待归档目录 --output 归档输出目录 --config project.yaml
py -3 -m archive_assistant apply --source 待归档目录 --output 归档输出目录 --config project.yaml
```

可选 `--zip`。移动必须 `allow_move: true` 且 `--confirm-move`。禁止覆盖、不删除源文件。

## 测试

```text
py -3 -m unittest tests.test_archive tests.test_classify tests.test_web -v
```
