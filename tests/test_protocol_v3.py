"""包路由与生成物的结构检查；模型行为由 evals 单独验收。"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import tempfile
import subprocess
import json
from html.parser import HTMLParser

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_visual", PACKAGE / "dev/generate_visual_map.py")
visual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual)


class SkillStructureTest(unittest.TestCase):
    def test_fulltext_search_navigation_and_links_share_source(self):
        page, _ = visual.build()
        class Links(HTMLParser):
            def __init__(self):
                super().__init__(); self.ids = []; self.links = []; self.refs = []
            def handle_starttag(self, tag, attributes):
                attrs = dict(attributes)
                if 'id' in attrs: self.ids.append(attrs['id'])
                if attrs.get('href', '').startswith('#'): self.links.append(attrs['href'][1:])
                if attrs.get('data-path', '').startswith('references/'): self.refs.append(attrs['data-path'])
        parsed = Links(); parsed.feed(page)
        self.assertEqual(len(parsed.ids), len(set(parsed.ids)))
        self.assertFalse(set(parsed.links) - set(parsed.ids))
        self.assertEqual(set(parsed.refs), {p.relative_to(PACKAGE).as_posix() for p in (PACKAGE/'references').glob('*.md')})
        self.assertIn('id="search"', page)

    def test_review_uses_frozen_git_trees_and_handles_renames_deletes_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
            git('init','-q'); git('config','user.name','Test'); git('config','user.email','test@example.invalid')
            (repo/'references').mkdir(); (repo/'templates').mkdir()
            (repo/'SKILL.md').write_text('---\nversion: 9.0.0\n---\n# 入口\n[旧](references/old.md)\n')
            (repo/'references/old.md').write_text('# 参考\n\n中文长行与特殊字符 <script>不执行</script>\n')
            (repo/'templates/gone.md').write_text('# 模板\n')
            (repo/'CHANGELOG.md').write_text('## [9.0.0]\n\n- 旧版说明。\n')
            git('add','.'); git('commit','-qm','base'); base=git('rev-parse','HEAD')
            git('mv','references/old.md','references/new.md')
            (repo/'SKILL.md').write_text('---\nversion: 9.1.0\n---\n# 入口\n[新](references/new.md)\n')
            (repo/'changed.txt').write_text('__CSS__ __LIBRARY__ __PATCH__ <script>not executable</script>\n')
            (repo/'CHANGELOG.md').write_text('## [9.1.0]\n\n- 新版收益来自同一份变更记录。\n\n## [9.0.0]\n\n- 旧版说明。\n')
            (repo/'templates/gone.md').unlink()
            git('add','.'); git('commit','-qm','target'); target=git('rev-parse','HEAD')
            (repo/'SKILL.md').write_text('UNCOMMITTED SECRET MUST NOT APPEAR')
            (repo/'CHANGELOG.md').write_text('UNCOMMITTED CHANGELOG MUST NOT APPEAR')
            document, info = visual.build_review(repo, base, target, asset_root=PACKAGE/'docs/assets/diff2html')
            self.assertIn(base, document); self.assertIn(target, document)
            self.assertIn('rename from references/old.md', info['patch'])
            self.assertIn('deleted file mode', info['patch'])
            self.assertNotIn('UNCOMMITTED SECRET', document)
            self.assertNotIn('UNCOMMITTED CHANGELOG', document)
            summary = re.search(r'<section id="changes">(.*?)</section>', document, re.S)[1]
            self.assertIn('新版收益来自同一份变更记录', summary)
            self.assertNotIn('旧版说明', summary)
            self.assertLess(document.index('id="changes"'), document.index('id="review"'))
            self.assertNotIn('<script>不执行</script>', document)
            self.assertIn('Diff2Html', document)
            embedded = re.search(r'<script id="patch-data" type="application/json">(.*?)</script>',document,re.S)[1]
            self.assertEqual(json.loads(embedded),info['patch'])
            empty, info = visual.build_review(repo, target, target, asset_root=PACKAGE/'docs/assets/diff2html')
            self.assertEqual(info['patch'], '')
            self.assertIn('没有文本差异', empty)
            with self.assertRaises(ValueError):
                visual.build_review(repo, '--all', target, asset_root=PACKAGE/'docs/assets/diff2html')
            git('tag','9.0.0',base)
            self.assertEqual(visual.previous_release(repo, target), '9.0.0')
            with self.assertRaises(ValueError):
                visual.previous_release(repo, base)

    def test_runtime_references_are_reachable_from_entrypoint(self):
        seen, queue = set(), [PACKAGE / "SKILL.md"]
        while queue:
            path = queue.pop()
            if path in seen:
                continue
            self.assertTrue(path.is_file(), str(path))
            seen.add(path)
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
                if ":" not in target and not target.startswith("#"):
                    linked = (path.parent / target.split("#")[0]).resolve()
                    self.assertTrue(linked.is_relative_to(PACKAGE))
                    if linked.suffix == ".md":
                        queue.append(linked)
        self.assertTrue(set((PACKAGE / "references").glob("*.md")) <= seen)

    def test_generated_page_is_current_and_reads_real_content(self):
        page, digest = visual.build()
        self.assertEqual(page, visual.OUTPUT.read_text())
        self.assertIn(digest, page)
        for path in (PACKAGE / "references").glob("*.md"):
            title = re.search(r"^# (.+)$", path.read_text(), re.M).group(1)
            self.assertIn(f"<summary>{title}</summary>", page)

    def test_new_route_and_changed_policy_render_without_fixed_wording(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir()
            (root / "templates").mkdir()
            (root / "SKILL.md").write_text("---\nversion: 9.0.0\n---\n# 新入口\n\n[新参考](references/new.md)\n")
            (root / "references/new.md").write_text("# 新参考\n\n新的规则，不要求阶段名称。\n")
            with patch.object(visual, "PACKAGE", root):
                first, old_digest = visual.build()
                (root / "references/new.md").write_text("# 新参考\n\n修改后的规则。\n")
                second, new_digest = visual.build()
            self.assertNotEqual(old_digest, new_digest)
            self.assertNotEqual(first, second)
            self.assertIn("修改后的规则", second)

    def test_renderer_escapes_document_markup_and_preserves_code(self):
        rendered = visual.render("# 标题\n\n<script>alert(1)</script>\n\n```\nx < y\n```\n")
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("x &lt; y", rendered)
        with self.assertRaises(ValueError):
            visual.render("```\nunclosed")

    def test_visual_routes_follow_source_conditions_and_supplementary_references(self):
        sources = {
            'SKILL.md': '# 入口\n\n| 缺口 | 参考 |\n|---|---|\n'
                        '| 用户在小屏查看 | [汇报](references/report.md)；仅小屏加读[小屏](references/mobile.md) |\n',
            'references/report.md': '# 汇报\n\n需要解释时使用。\n',
            'references/mobile.md': '# 小屏\n\n只在小屏使用。\n',
            'references/extra.md': '# 补充\n\n仅在特殊条件使用。\n\n后续细节。\n',
        }
        page = visual.routing(sources)
        self.assertEqual(page.count('class="module-row"'), 2)
        self.assertIn('用户在小屏查看', page)
        self.assertIn('仅小屏加读', page)
        self.assertIn('仅在特殊条件使用', page)
        self.assertNotIn('后续细节', page)
        for path in sources.keys() - {'SKILL.md'}:
            self.assertIn('#' + visual.anchor(path), page)
        sources['SKILL.md'] = sources['SKILL.md'].replace('用户在小屏查看', '另一个触发条件')
        self.assertNotIn('用户在小屏查看', visual.routing(sources))

    def test_decision_paths_and_stop_conditions_come_from_the_root(self):
        source = '# 入口\n\n## 判断当前请求\n\n| 条件 | 动作 | 结束 |\n|---|---|---|\n| 只读 | 查证 → 回答 | 不改文件 |\n\n## 推进与停止\n\n| 状态 | 动作 |\n|---|---|\n| 有未完成工作 | 继续 |\n| 已完成 | 结束 |\n'
        self.assertEqual(visual.table_rows(visual.section(source, '判断当前请求'), 3), [['只读', '查证 → 回答', '不改文件']])
        self.assertIn('不改文件', visual.decisions(source))
        self.assertIn('有未完成工作', visual.outcomes(source))
        updated = source.replace('不改文件', '在指定边界结束')
        self.assertNotIn('不改文件', visual.decisions(updated))
        self.assertIn('在指定边界结束', visual.decisions(updated))

    def test_reader_preserves_the_complete_markdown(self):
        page, _ = visual.build()
        class RawSources(HTMLParser):
            def __init__(self):
                super().__init__(); self.path = None; self.raw = False; self.pre = False; self.sources = {}
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('class') == 'reference': self.path = attrs['data-path']
                if attrs.get('class') == 'raw-source': self.raw = True
                if tag == 'pre' and self.raw: self.pre = True; self.sources[self.path] = ''
            def handle_data(self, data):
                if self.pre: self.sources[self.path] += data
            def handle_endtag(self, tag):
                if tag == 'pre': self.pre = False; self.raw = False
        raw = RawSources(); raw.feed(page)
        for path, contents in raw.sources.items():
            self.assertEqual(contents, (PACKAGE/path).read_text())
        self.assertEqual(set(raw.sources), {'SKILL.md', *(p.relative_to(PACKAGE).as_posix() for p in (PACKAGE/'references').glob('*.md'))})


class FileMapTest(unittest.TestCase):
    def test_file_map_covers_every_packaged_file_and_every_routed_reference(self) -> None:
        manifest = json.loads((PACKAGE / "workflow-package.json").read_text(encoding="utf-8"))
        files = set(manifest["runtime"]["files"]) | set(manifest["source_only"]) | {"workflow-package.json"}
        page, _ = visual.build()
        section = page[page.index('<section id="files"'):page.index('<section id="changes"')]
        panels = set(re.findall(r'class="map-panel" data-path="([^"]+)"', section))
        self.assertEqual(panels, files)
        routed = {path for _, path in visual.LINK.findall((PACKAGE / "SKILL.md").read_text(encoding="utf-8")) if path.startswith("references/")}
        self.assertEqual(len(routed), len(list((PACKAGE / "references").glob("*.md"))))
        nodes = set(re.findall(r'<g class="n [^"]*" data-go="([^"]+)"', section))
        self.assertLessEqual(routed, nodes)


if __name__ == "__main__":
    unittest.main()
