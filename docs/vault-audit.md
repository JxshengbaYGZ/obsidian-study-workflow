# 知识库结构审计工具

`scripts/audit_vault.py` 只读取用户明确给定的实际 vault 根目录，不跟随符号链接、Windows 联接点或其他重解析目录，不读取隐藏配置或插件，不访问网页，不自动修改笔记。

```powershell
python -X utf8 scripts/audit_vault.py 'D:\我的自编知识库' --output 'D:\审计结果'
python -X utf8 -m unittest discover -s tests -p 'test_audit_vault.py' -v
```

输出 `audit.json` 保存全量链接和逐行待处理项，`report.md` 便于阅读。输出位置必须在被审计库之外。没有私人默认目录、账户信息或现有笔记内容；测试库完全自编并在运行后清理。

解析 wiki 目标、标题锚点、块 ID、PDF 页锚点、表格中转义的 wiki 别名、平衡括号 Markdown 路径和 HTML 图片。短名对应多个文件时登记歧义；其他 vault URI、绝对路径、越出根目录的链接单独登记，不把跨库未读文件说成已坏。数学公式、代码、HTML 表格字面单位括号不作为导航。

此工具是结构门禁，不能替代逐卡核源、数学推导、裁图完整性、网页可达性或 Obsidian 客户端阅读验收。无入链、未被嵌入的附件、完全相同的内容只是整理候选；删除或合并之前应检查用途并留兼容入口。
