# 记录与质量

## 知识点

自然标题；定义与条件；使用方法；具体算例；解释了关系的关联知识；关联题目；应用与迁移（有实质内容才写）；来源页码或时间戳。不要重复正文标题。

## 题卡

题意标题；醒目完整题干；可折叠标准解答；关键方法与易错点；原题裁图；实际存在的原作答裁图；来源文件/页/题；解释关系的知识点链接。折叠方式沿用库内验证可用的样例。

## 审查台账

每个项目记录 id、类型、来源类型、状态、来源核对、语义检查、具体证据、处置理由、输出文件、实际审查者。状态为 unread、pending、verified、corrected、duplicate、no_independent_tip。未发布不等于拒绝，重复需指向已有卡，无独立技巧需说明原因。

证据可以是题卡段落、原图位置和计算记录的短指针，不复制推导全文。批量公共的链接/同步结果写一份，逐项引用。可额外记录self_review和final_review（pending/passed/failed/blocked），以区分执行者自检与阶段末独立复核；旧台账未注明复核层级不能据此宣称完成独立复核。全部完成的口径仍需来源范围和最终复核记录共同支持。

可用 scripts/ledger_check.py 检查 JSON 结构。顶层 expected_ids 是完整范围，items 是记录。每项要求 id、kind（topic/question/tip）、source_kind（scan/transcript/authored）、status、source_check（unread/matched/unclear/not_applicable）、semantic_check（unread/passed/failed/blocked）、evidence（列表）、reason。verified/corrected 必须有通过的语义检查与具体证据，扫描/字幕须来源 matched，自编内容可 not_applicable。

脚本仅验证台账一致性，不能证明作者真的看过图片或数学结论正确。--require-complete 用于要求无 unread/pending 的交付，不改变证据标准。

expected_ids 必须与独立来源清单核对：保存文件、总页数或完整时间段及覆盖映射。只把已抽出的候选填进 expected_ids 不能证明原材料全部覆盖；输出报告须明确是候选范围还是完整来源范围。

按卡片文件交付时，使用 `scripts/check_card_coverage.py ROOT --cards questions topics --ledger ledger.json --manifest manifest.json` 将实际卡片与台账、清单对照；目录名可替换为项目自己的名称。每张题卡和知识点卡应有对应的 `output_file`，只登记题卡不能代表知识点已审查。此检查发现漏卡和路径问题，不证明语义或原图正确。最终公式检查对全部已落盘Markdown运行，避免漏掉稍后补写的state。

duplicate_of 必须指向本批记录或顶层 existing_ids 中登记的已有条目，不能自指或循环；existing_ids 仍需实际查文件。判断重复或无独立技巧前必须读对应来源，不能把未读项目这样归类来通过完成检查。

## 审查次序

`final_review=passed` 必须附 `final_review_record`：`reviewer`、`mode=independent`、`evidence`、`scope`。同一执行者二次自检不填独立通过；结构门禁只检查记录，不能证明审查真实发生。审查旧试跑时保留原件，用旁附审查记录撤回不实状态，不覆盖原始实验数据。

1. 对照源文件确认题干、数据、上下限和符号。
2. 独立求解，再比较已有答案。保留原作答中的错误，另写纠正说明。
3. 查成立条件和特殊值，至少做针对本题的独立复算。
4. 同步题卡、笔记展示、答案和生成源；将题卡中的每个嵌入附件列入清单，逐个确认 vault 中存在且非空，再读回 Markdown 核对内容。
5. 核对链接、折叠、公式、裁图以及来源未被改写。

范围报告分别列：实际读取的知识点、逐题语义审查、原图核对页/题、来源待补证、链接和公式机械检查。不得合并成含混的“全部通过”。
