from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "publishing-wechat-articles"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tests.voice_helpers import valid_brief, valid_review
from wechat_pipeline.config import load_repository_config
from wechat_pipeline.voice import (
    VoiceError,
    load_evidence_ids,
    load_voice_profile,
    validate_article_personal_claims,
    validate_author_brief,
    validate_voice_review,
)


class VoiceProfileTest(unittest.TestCase):
    def setUp(self):
        self.config = load_repository_config(SKILL)

    def test_profile_merges_author_core_with_account_overlay(self):
        profile = load_voice_profile(self.config, "tech")

        self.assertEqual(profile.schema_version, 1)
        self.assertEqual(profile.account, "tech")
        self.assertIn("attention", profile.author)
        self.assertIn("audience", profile.overlay)
        self.assertRegex(profile.profile_sha256, r"^[0-9a-f]{64}$")

    def test_account_overlays_do_not_mix(self):
        tech = load_voice_profile(self.config, "tech")
        parenting = load_voice_profile(self.config, "parenting")

        self.assertNotEqual(tech.overlay["audience"], parenting.overlay["audience"])
        self.assertNotEqual(tech.profile_sha256, parenting.profile_sha256)

    def test_brief_requires_increment_and_three_distinct_titles(self):
        payload = valid_brief()
        payload["incremental_value"] = ""
        with self.assertRaisesRegex(VoiceError, "incremental_value"):
            validate_author_brief(payload, expected_profile_sha256="a" * 64, evidence_ids=set())

        payload = valid_brief()
        payload["title_candidates"] = ["同一个", "同一个", "另一个"]
        with self.assertRaisesRegex(VoiceError, "title_candidates"):
            validate_author_brief(payload, expected_profile_sha256="a" * 64, evidence_ids=set())

    def test_personal_claim_requires_indexed_evidence(self):
        payload = valid_brief()
        payload["personal_claims"] = [
            {"claim": "我曾经上线过这套系统", "evidence_id": "launch-1"}
        ]

        with self.assertRaisesRegex(VoiceError, "launch-1"):
            validate_author_brief(payload, expected_profile_sha256="a" * 64, evidence_ids=set())

        normalized = validate_author_brief(
            payload,
            expected_profile_sha256="a" * 64,
            evidence_ids={"launch-1"},
        )
        self.assertEqual(normalized["personal_claims"][0]["evidence_id"], "launch-1")

    def test_article_rejects_personal_experience_missing_from_brief(self):
        brief = valid_brief()

        with self.assertRaisesRegex(VoiceError, "undeclared personal experience"):
            validate_article_personal_claims("我曾经上线过这套系统。", brief)

        brief["personal_claims"] = [
            {"claim": "我曾经上线过这套系统", "evidence_id": "launch-1"}
        ]
        validate_article_personal_claims("我曾经上线过这套系统。", brief)

    def test_article_does_not_treat_normal_first_person_transition_as_experience(self):
        validate_article_personal_claims("我们来看这套系统的边界。", valid_brief())

    def test_review_binds_to_current_article_and_real_excerpts(self):
        payload = valid_review(article_sha256="b" * 64)
        with self.assertRaisesRegex(VoiceError, "article_sha256"):
            validate_voice_review(
                payload,
                expected_article_sha256="c" * 64,
                article_markdown="正文原句",
            )

        payload = valid_review(article_sha256="c" * 64, excerpt="不存在的句子")
        with self.assertRaisesRegex(VoiceError, "excerpt"):
            validate_voice_review(
                payload,
                expected_article_sha256="c" * 64,
                article_markdown="正文原句",
            )

    def test_passing_review_requires_all_dimensions_present(self):
        payload = valid_review(article_sha256="c" * 64)
        payload["dimensions"][0]["status"] = "weak"

        with self.assertRaisesRegex(VoiceError, "pass decision"):
            validate_voice_review(
                payload,
                expected_article_sha256="c" * 64,
                article_markdown="正文原句",
            )

    def test_evidence_index_rejects_paths_outside_voice_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            voice_root = Path(tmp)
            (voice_root / "evidence.toml").write_text(
                'schema_version = 1\n[[evidence]]\nid = "escape"\nkind = "note"\npath = "../outside.md"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(VoiceError, "outside voice vault"):
                load_evidence_ids(voice_root)


if __name__ == "__main__":
    unittest.main()
