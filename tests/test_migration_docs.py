from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'publishing-wechat-articles'


class MigrationDocumentationTest(unittest.TestCase):
    def test_handoff_uses_real_repository_relative_paths(self):
        playbook = (SKILL / 'references/editorial-playbook.md').read_text(encoding='utf-8')
        for relative in (
            'AGENTS.md',
            'publishing-wechat-articles/SKILL.md',
            'publishing-wechat-articles/scripts/pipeline.py',
            'publishing-wechat-articles/references/editorial-playbook.md',
        ):
            self.assertIn(f'`{relative}`', playbook)
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertNotIn('本仓库 `scripts/pipeline.py`', playbook)

    def test_maintenance_paths_share_repository_root(self):
        migration = (ROOT / 'MIGRATION.md').read_text(encoding='utf-8')
        maintenance = migration.split('## 以后只维护哪里', 1)[1]
        for relative in (
            'publishing-wechat-articles/SKILL.md',
            'publishing-wechat-articles/references/editorial-playbook.md',
            'publishing-wechat-articles/references/*-contract.md',
            'publishing-wechat-articles/scripts/wechat_pipeline/',
            'scripts/bootstrap.py',
        ):
            self.assertIn(f'`{relative}`', maintenance)
            self.assertTrue(list(ROOT.glob(relative)), relative)

    def test_migration_does_not_claim_login_or_paid_generation(self):
        migration = (ROOT / 'MIGRATION.md').read_text(encoding='utf-8')
        for phrase in ('不复制登录 token', '本次没有付费调用', '不代表远端写权限', '不等于已完成真实 Agent 对话验收'):
            self.assertIn(phrase, migration)
        skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('references/editorial-playbook.md', skill)


if __name__ == '__main__':
    unittest.main()
