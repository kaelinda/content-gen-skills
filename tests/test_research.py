from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'publishing-wechat-articles/scripts'))
from wechat_pipeline.research import check_research


def dossier():
    return {
        'reader': '后端开发者', 'problem': '判断是否接入 SDK',
        'benefit': '用权限隔离清单验收接入', 'increment': '给出失败回滚检查',
        'gift_review': '愿意推荐给正在做选型的朋友；删去无关发布消息。',
        'official_available': True,
        'duplicate_check': {'scope': '本地归档与最近飞书记录，非全部历史', 'result': 'distinct'},
        'sources': [
            {'id': 'docs', 'url': 'https://example.com/docs', 'kind': 'official', 'status': 'read', 'excerpt': 'SDK supports tools'},
            {'id': 'release', 'url': 'https://example.com/releases', 'kind': 'official', 'status': 'read', 'excerpt': 'Tools are available in preview'},
        ],
        'claims': [{'text': '预览版支持工具', 'source_ids': ['docs', 'release'], 'status': 'verified', 'kind': 'official_claim', 'material': True}],
        'limitations': ['未本地实测，多份官方文档不等于独立测试'],
    }


class ResearchTest(unittest.TestCase):
    def test_prepare_blocks_invalid_research_and_deleted_dossier(self):
        import json
        import tempfile
        from wechat_pipeline.config import load_repository_config
        from wechat_pipeline.orchestrator import Pipeline, PipelineError
        from wechat_pipeline.models import Stage
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pipeline = Pipeline(load_repository_config(root / 'publishing-wechat-articles'), workspace)
            pipeline.plan('SDK 权限隔离实战：上线前的验收清单', '权限隔离', 'tech', run_id='evidence')
            run = workspace / 'runs/evidence'
            (run / 'article.md').write_text('## SDK 权限隔离实战\n\n上线前的验收清单。\n', encoding='utf-8')
            (run / 'research.json').write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(PipelineError, 'research evidence'):
                pipeline.prepare('evidence', render_png=False)
            self.assertEqual(pipeline.status('evidence').state, Stage.NEEDS_REVIEW)
            (run / 'research.json').unlink()
            with self.assertRaisesRegex(PipelineError, 'research evidence'):
                pipeline.prepare('evidence', render_png=False)
            self.assertFalse((run / 'article.html').exists())

    def test_complete_dossier_passes_without_claiming_independence(self):
        self.assertTrue(check_research(dossier())['passed'])

    def test_reader_value_is_required(self):
        data = dossier(); data['benefit'] = ''
        self.assertFalse(check_research(data)['passed'])

    def test_snippet_is_not_read_evidence(self):
        data = dossier(); data['sources'][1]['status'] = 'discovered'
        self.assertFalse(check_research(data)['passed'])

    def test_official_source_required_when_available(self):
        data = dossier()
        for source in data['sources']: source['kind'] = 'secondary'
        self.assertFalse(check_research(data)['passed'])

    def test_single_source_requires_attribution_and_limitation(self):
        data = dossier(); data['claims'][0]['source_ids'] = ['docs']
        self.assertFalse(check_research(data)['passed'])
        data['claims'][0].update(status='attributed', limitation='仅官方声明，未独立验证')
        self.assertTrue(check_research(data)['passed'])

    def test_conflicting_central_claim_blocks(self):
        data = dossier(); data['claims'][0]['status'] = 'conflicted'
        self.assertFalse(check_research(data)['passed'])

    def test_duplicate_urls_do_not_count_twice(self):
        data = dossier(); data['sources'][1]['url'] = data['sources'][0]['url']
        self.assertFalse(check_research(data)['passed'])

    def test_unknown_reference_and_unsafe_url_block(self):
        data = dossier(); data['claims'][0]['source_ids'] = ['missing', 'docs']
        self.assertFalse(check_research(data)['passed'])
        data = dossier(); data['sources'][0]['url'] = 'file:///etc/passwd'
        self.assertFalse(check_research(data)['passed'])

    def test_malformed_data_returns_findings(self):
        for data in ([], {}, {'sources': None}, dict(dossier(), claims=['bad'])):
            with self.subTest(data=data):
                self.assertFalse(check_research(data)['passed'])

    def test_duplicate_needs_explicit_new_angle(self):
        data = dossier(); data['duplicate_check']['result'] = 'duplicate'
        self.assertFalse(check_research(data)['passed'])
        data['duplicate_check'].update(result='new-angle', difference='从入门介绍转向权限隔离验收')
        self.assertTrue(check_research(data)['passed'])
