---
name: complete-lab-report
description: Complete or revise a course experiment report from a DOCX template, handout, program code, measured data, and result screenshots. Use for Chinese 实验报告 tasks that require matching figures to experiment steps, filling analysis and questions, preserving the original layout, and verifying the final file.
---

# Complete Lab Report

## Establish the evidence

1. Read the experiment handout and the supplied report template before drafting. Map each required task and question to a source of evidence: code, measured values, screenshots, or theory. Preserve the template's existing headings, equations, table fields, and layout when editing it.
2. Inspect every supplied screenshot at readable resolution. Match it to the code's input parameters, figure title, axes, units, and output. Use the actual plots as observations; do not describe expected results as though measured. Flag a blank plot, repeated parameter set, missing figure, inconsistent labels, or code error explicitly.
3. Distinguish observed results, calculations from known parameters, and theoretical interpretation. Never fabricate measurements, time, place, instrument, teacher, or missing personal details. Fill only identity fields the user supplies. Keep other fields blank unless their value is present in a source.

## Write the report

1. Work in the given DOCX when possible. Keep the original title and experiment order. Put each numbered figure close to its own result analysis, with an unambiguous caption. Explain numerical choices such as sampling frequency, sample interval, number of effective samples, FFT length, observation duration, and frequency grid width where they affect interpretation.
2. State axis units correctly. Frequency in Hz differs from angular frequency in rad/s. A phase angle is in rad; a dimensionless digital sequence has no physical amplitude unit unless the source assigns one. Do not silently label a normalized FFT as raw amplitude.
3. Explain the mechanism behind a visual change: aliasing from undersampling, leakage from finite observation, denser interpolation from zero padding, and genuine resolving power from longer observation. Do not equate zero padding with new information. If two runs have the same parameters, report that their plots duplicate and do not invent a comparison.
4. Answer every requested discussion question using the actual experiment parameters. Keep concise causal paragraphs, not generic textbook filler. For code or equations that cannot be verified from the supplied sources, label assumptions or leave a clearly marked unresolved item.

## Verify before delivery

1. Use the document-authoring skill's render-and-inspect procedure: render the DOCX to page images, inspect every page, correct clipping, glyph loss, split captions, oversized plots, and empty trailing pages, then render again. If the local renderer lacks the template's Chinese fonts, inspect the document XML for complete Chinese text and report the rendering limitation honestly instead of claiming visual perfection.
2. Confirm that every required figure exists once, that its caption and analysis refer to the same parameter set, and that all requested questions are answered. Recheck personal-information fields and leave unspecified fields untouched.
3. Save the edited document as a new version of its existing Library file when it is Library-backed, unless the user explicitly requests a separate copy. Deliver a link to the final document and briefly mention any unresolved source-data limitation.
