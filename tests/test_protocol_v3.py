"""包路由与生成物的结构检查；模型行为由 evals 单独验收。"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_visual", PACKAGE / "scripts/generate_visual_map.py")
visual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual)


class SkillStructureTest(unittest.TestCase):
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
            (root / "templates/work.md").write_text("# 恢复记录\n")
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


if __name__ == "__main__":
    unittest.main()
