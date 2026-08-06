from __future__ import annotations


def valid_brief(profile_sha256: str = "a" * 64) -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_sha256": profile_sha256,
        "reader_problem": "读者只能得到一组去 AI 味词表",
        "source_baseline": "现有方案依赖固定禁用表达",
        "incremental_value": "把作者判断和证据变成写作前置条件",
        "thesis": "作者声音来自持续的内容选择，而不是口头禅",
        "tension": "统一反套路规则会制造新的统一套路",
        "reasoning_moves": ["描述现状", "指出二阶结果", "给出数据契约"],
        "evidence_refs": [],
        "personal_claims": [],
        "counterpoint": "机械检查仍适合发现结构和安全问题",
        "excluded_directions": ["本期不做模型微调"],
        "title_candidates": [
            "作者声音不是另一份禁词表",
            "去掉 AI 味之后，还剩下谁的判断",
            "把作者声音放进写作流水线",
        ],
    }


def valid_review(article_sha256: str = "b" * 64, excerpt: str = "正文原句") -> dict[str, object]:
    return {
        "schema_version": 1,
        "article_sha256": article_sha256,
        "decision": "pass",
        "dimensions": [
            {
                "name": name,
                "status": "present",
                "excerpts": [excerpt],
                "note": f"{name} 有明确落点",
            }
            for name in ("attention", "judgment", "reasoning", "evidence", "language")
        ],
        "blockers": [],
        "anonymous_paragraphs": [],
    }
