# 可恢复的正式批处理

本页是脚本的完整输入约定；无需旧聊天。先完成一个小章节，再扩展同一学科。核心脚本只需 Python 3.9+ 标准库；PDF 裁图额外需要 PyMuPDF，网页预览额外需要 Node、marked、KaTeX、Playwright 和可启动的浏览器。已有环境可传模块路径，无须反复安装。

## 最短执行路径

在仓库根目录运行，`batch` 是私有工作目录，`output` 是独立知识库目录，两者不要嵌套。

```sh
python skills/study-knowledge-base/scripts/kb.py init batch --output output --batch logic --title "命题逻辑"
# 清点当前完整来源单元，填写 plan.json、逐题 statement 文件
python skills/study-knowledge-base/scripts/kb.py freeze batch
# 写 drafts；每条随写自检，结束后一次集中构建
python skills/study-knowledge-base/scripts/kb.py build batch
# 对构建版本进行来源、专业内容、实际排版复核，写 review.json
python skills/study-knowledge-base/scripts/kb.py check batch
python skills/study-knowledge-base/scripts/kb.py publish batch
python skills/study-knowledge-base/scripts/kb.py status batch
```

命令非零退出时先读具体错误，不继续发布。`status` 是已保存进度；`check/publish` 会重新核对，历史通过不代表当前通过。重复发布未变化批次应返回 `changed_files: 0`。

## 输入与来源

`project.json`：

```json
{"version":1,"batch_id":"logic","title":"命题逻辑","output_dir":"../output","require_independent":true}
```

相对路径以批次目录为基准；初始化命令生成绝对输出路径，搬迁时在首次冻结前改成相对路径。批次 ID 和条目 ID 用字母、数字、下划线或连字符，不用页码猜题号。跨批次保留同一概念 ID；查输出目录 `.kb/catalog.json`，先复用既有知识点，避免换标题重复建卡。

`plan.json` 最小结构：

```json
{
  "sources":[{"id":"src1","path":"sources/q1.png","kind":"image","location":"原卷.pdf，PDF物理第2页，第三题"}],
  "items":[
    {"id":"concept","kind":"topic","title":"自然知识点标题","provenance":"authored","state":"ready","source_ids":[]},
    {"id":"exercise","kind":"question","title":"自然题目标题","provenance":"original","state":"ready","source_ids":["src1"],"statement":"statements/exercise.md","related":[{"id":"concept","reason":"用该定义检查此题的条件"}]}
  ],
  "learning_order":["concept"]
}
```

- 来源类型：`image/text/pdf/transcript`。图像必须实际打开；PDF 扫描题须逐题裁图，不能只给整卷链接。题干与图形、可能影响条件的手写补充都需看清；原作答保留图，不强行解释重叠笔迹。
- 可用 `prepare_source.py 原卷.pdf --page 2 --rect 0.05 0.20 0.95 0.45 --output batch/sources/q1.png` 裁图。坐标为归一化边界，页码为物理页；邻接 `.source.json` 记录原文件摘要与坐标。裁到 PDF 边缘不证明原纸完整。
- 文本/字幕来源应是实际完整相关段落，保存时间戳/页码和前后文；OCR 文本需与原图同时保存。程序不代替 OCR，也不会猜图形条件。
- `provenance=original` 必须有来源；`authored` 表示整理者补充/自编，不能包装成原稿。知识点综合了原文与补充时，在正文分别标明；关联关系不能只写“相关”。
- `learning_order` 按前置关系完整列本批知识点。对清单逐项记录已收录、重复、待补证、无独立内容或未审查；计划外材料不算已处理。现有程序只检查已声明计划，不能证明你已通读全部原材料。
- 待补证条目用 `state=pending`、`reason` 和原始来源。它只展示中性标题和原图，不发布猜测题干/答案；复核记录给出具体下一步。发现题干问题应保留原题，不静默补条件。

冻结绑定配置、清单、原材料和题干。不要修改冻结数据后删除状态来假装旧审查有效：题干或计划改变时新建修订批次，复制必要来源、保留稳定条目 ID，重新核源和冻结；旧批次保留。仅修改解答/笔记正文时可原批次重新 `build`，新版本必须重审受影响内容。

## 正文与省 token 分工

正文放 `drafts/<id>/`：知识点/技巧为 `body.md`；题目为 `answer.md` 和 `method.md`，题干只读冻结的 `statement`。不要在正文写一级标题、本地链接或再次包装“标准解答”；程序统一生成。数学只用 `$...$`、`$$...$$`，矩阵和多行推导保留实际换行。

编写者只读本批源单元、定义约定和最接近的已有卡，输出正文与简短自检证据。知识点包括定义、范围、前提、具体短例、易错点；解答包含关键推导、条件检查与可独立复算的结果；技巧包含触发条件、操作和反例/禁用条件，不凑数量。主解应符合学习顺序，高阶捷径只作可选补充。

推荐任务说明：

> 按 plan 的冻结题干与原图完成所有 drafts；原作答不作答案依据。统一记号，逐题复算最易错处，记录证据路径，不复述整份规则。不写发布批准，不改源数据；疑点单列供主控修订计划。范围结束一次集中交付。

独立复核者读取来源、题干、成品和必要定义，独立算关键结果，再对照解答；集中复核完整小批，不要求每一道题切一次模型。可使用另一执行者或隔离的复算程序，但不能把作者自报当独立复核。首次学科/新题型扩大核验；稳定内容复用已有已核定义。不要反复读整库或重复生成同一题卡。

## 排版和审查记录

`build` 返回 `.kb/build/<revision>/`。可在 Obsidian 实际查看，也可运行：

```sh
node skills/study-knowledge-base/scripts/preview.mjs BUILD目录 --output batch/evidence/preview
```

模块不在默认搜索路径时传 `--katex-module`、`--katex-css`、`--marked-module`、`--playwright-module`；浏览器可传 `--channel msedge` 或 `--browser-executable`。脚本生成每卡截图与 420/960 宽度检查。必须实际看截图，检查公式、真值表、图片、折叠和阅读顺序；网页预览不能声称 Obsidian 原生已验收。跨批次既有链接以正式输出为准核查，预览目录不复制整库。

`review.json` 绑定 `build` 返回的完整 revision，每个计划条目都要有一行：

```json
{
  "revision":"从实际build复制的完整值",
  "items":[
    {"id":"concept","decision":"approved","semantic_check":"passed","source_check":"not_applicable","mode":"independent","reviewer":"实际审查者","scope":"具体核对范围","evidence":["evidence/review.md"]},
    {"id":"exercise","decision":"approved","semantic_check":"passed","source_check":"matched","mode":"independent","reviewer":"实际审查者","scope":"原图条件、推导和具体复算","evidence":["evidence/review.md"]}
  ],
  "presentation":{"status":"passed","method":"实际使用的渲染器","scope":"实际看过的全部卡片及限制","evidence":["evidence/preview/result.json","evidence/preview/card-1.png"]}
}
```

这只是字段示例，禁止直接复制批准状态作为真实验收。`not_applicable` 仅用于无引用来源的自编补充；待核项 `decision=pending` 并填 `next_action`。证据需真实存在并记录发现/计算，不能空文件或只写“通过”。缺复核、漏卡、旧版本、数学排版警告均阻止发布；先修正文/记录再重建。自检、机械检查、内容复核分别报告，不以 JSON 合规冒充数学正确。

## 发布、恢复与后续科目

程序输出 `笔记/题/技巧/章节/原始资料/整理记录`，生成稳定文件名和有解释的关联，同批次双向连接；跨批次引用不会自动改写老卡的反向链接，如需双向导航将老卡纳入下一修订批次。来源、审核证据按内容摘要保存，已有版本备份。审查记录中记录范围，不声称全学科已处理。

发布前检查全部冲突。未登记的旧文件或手工修改会拦截覆盖：保留编辑内容，在新修订批次整合，或选择新的独立输出目录；不要抹掉目录登记来强推。已有库可先在独立小章节输出跑通后逐步迁入，不直接覆盖整个老库。

构建中断可原命令重跑；发布中断用相同批次、相同版本重跑 `publish`。未完成日志会阻止其他批次混入；文件逐个原子写入，但整个批次不是数据库事务，中断期间应暂缓阅读半批结果。完成后再次 `publish` 验证零变更。程序保留旧文件，不自动清理历史/退役卡；退役需明确迁移方案。

每批只报告：实际处理的材料/知识点/题/技巧数量，待补证数，复核范围，排版方式，重复发布结果。时间和 token 有实测才报告，无数据不推测节省比例。下一科复制配置和空清单，替换来源与定义约定，复用脚本，不复制上一科答案。
