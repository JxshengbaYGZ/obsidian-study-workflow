# 可运行自编小样

这是自编集合题，不是用户原稿。复制整个目录到私有位置，按需修改 `project.json` 输出路径，然后在仓库根目录运行：

```sh
python skills/study-knowledge-base/scripts/kb.py freeze examples/portable-demo
python skills/study-knowledge-base/scripts/kb.py build examples/portable-demo
python skills/study-knowledge-base/scripts/kb.py check examples/portable-demo
```

最后一步应因未复核而失败。实际核对两个条目、渲染并看图，依照 `references/portable-workflow.md` 创建真实 `review.json` 后才能发布。仓库不提供虚构的已批准记录。
