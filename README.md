# Obsidian 学习资料整理工作流

把教材、课程笔记、视频字幕和练习整理成能回查来源的 Obsidian 知识库。本仓库只提供通用流程、检查脚本和虚构小样；不收录任何人的教材、字幕、笔记或处理记录。

## 从哪里开始

| 任务 | 入口 |
|---|---|
| 学校课程：教材与笔记双向对应 | [学校课程工作流](docs/school-course-workflow.md) |
| 单个 Clipping、课件或教材持续补一张卡 | [多来源增补方法](docs/incremental-source-completion.md) |
| 扫描教材：原页、正文、图和知识点 | [教材库流程](docs/textbook-library.md) · [Skill](skills/textbook-library/SKILL.md) |
| 笔记、题目、字幕：来源与独立复核 | [知识库流程](docs/workflow.md) · [Skill](skills/study-knowledge-base/SKILL.md) |
| 控制模型调用与返工 | [按页分流与费用记录](docs/low-cost-textbook-transcription.md) |
| 运行虚构小样 | [便携小样](examples/portable-demo/README.md) |
| 既有知识库重构、内容纠错与增量迁移 | [重构与分层验收](docs/vault-refactor-and-verification.md) |
| 全量检查内部链接、锚点、附件与重复 | [只读结构审计工具](docs/vault-audit.md) |
| 比较原作者的外部工作流候选 | [GitHub 来源核查](docs/github-reuse-2026-10.md) |

## 最小流程

1. 固定原件、版本和可回查位置；教材页、课件页或视频时间片均可单独启动。
2. 完成一张可回源的概念卡：定义、条件、短例与来源贡献；新来源只补实际新增的内容。
3. 有教材对应小节时做教材卡与课程笔记双向链接；没有对应处就标明“无专节”。
4. 分别做机械检查、原页核对、专业复算和客户端预览，留下尚未审定的范围。
5. 通过一个小批次后再扩展；只重跑受影响的页面和文件。

工具检查的是结构和证据记录，不能替代对公式、图和题意的人工判断。[验证边界](docs/validation.md)说明如何报告结果。

## 隐私边界

公开仓库只接收通用方法、虚构例子、脚本与测试。真实教材 PDF、OCR/Markdown 原文、视频字幕、个人笔记、账户路径、页码台账和模型调用日志均保留在使用者自己的设备上。公开方法文档使用占位名，不复制个人项目的复盘。
