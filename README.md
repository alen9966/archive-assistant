# 项目资料归档助手

**同事直接打开即可用：** https://alen9966.github.io/archive-assistant/

请用 **Chrome 或 Edge**。点「选择资料文件夹」→ 自动分类 → 再选一个空文件夹保存。文件只在本机处理，不会上传。

源码：https://github.com/alen9966/archive-assistant

## 本机 Python 版（可选）

```text
py -3 -m pip install -r requirements.txt
py -3 -m archive_assistant web
```

然后打开 `http://127.0.0.1:8765/`。大 Altium 工程请用本机目录，不要浏览器上传。`History` / `__Previews` / `Project Logs` 默认跳过。

## 配置

复制 `project.example.yaml` 为 `project.yaml`，只填已知字段，不要编造。

## 命令行

```text
py -3 -m archive_assistant plan --source 待归档目录 --output 归档输出目录 --config project.yaml
py -3 -m archive_assistant apply --source 待归档目录 --output 归档输出目录 --config project.yaml
```

## 测试

```text
py -3 -m unittest tests.test_archive tests.test_classify tests.test_web -v
```

