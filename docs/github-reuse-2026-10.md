# GitHub 现成流程核查（2026-10-10）

本次只阅读原作者公开仓库与官方文档，没有安装这些项目，也没有在个人库中试运行。现有知识库检查程序继续维护；仅把可复用设计作为后续小样的候选。

| 原始来源 | 可借鉴范围 | 本轮证据与边界 |
|---|---|---|
| [white638/codex-obsidian-workflow](https://github.com/white638/codex-obsidian-workflow) | 章节检索、原文回读、链接审计、快照哈希、写入漂移保护与恢复 | 作者 README 描述这些能力；本轮未在 Windows 或当前库运行，不把上游 CI 当本机证明 |
| [Obsidian 官方 CLI 文档](https://github.com/obsidianmd/obsidian-help/blob/master/en/Extending%20Obsidian/Obsidian%20CLI.md) | 通过运行中的客户端读取、检索与开发者截图，补实际客户端证据 | 官方文档要求对应安装器与 CLI 注册；本轮未确认本机版本及注册状态，不自动启动或改设置 |
| [DavidAnson/markdownlint](https://github.com/DavidAnson/markdownlint) | Markdown 标题、表格、空行等格式检查 | 作者项目为静态格式检查；不能审查学科结论或代替 Obsidian 专有链接解析，本轮未安装 |

## 采用顺序

先使用当前检查器解决已确认的问题。若仍有中文检索、复杂链接或客户端证据缺口，再用自编隔离小库比较候选方案；固定相同输入与验收清单，记录具体版本、实际运行结果和遗漏。迁移已有库前保留旧结果，修复方法只按核定差异增量应用。

来源发现、作者说明、上游 CI、本机运行和专业语义复核分别记录。找到项目不等于获取或安装，安装不等于目标功能已验证。
