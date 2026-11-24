"""Keep balanced project READMEs separate from complete printable manuals."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit, unquote


ROOT = Path(__file__).resolve().parents[1]


class LocalImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.sources.extend(value for key, value in attrs if key == "src")


class DocumentationLayoutTests(unittest.TestCase):
    def test_homepages_keep_the_stepwise_sic_workflow_at_about_one_third_length(self):
        for name, guide in (("README.md", "user_guide.md"),
                            ("README.zh-CN.md", "user_guide.zh-CN.md")):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                manual = (ROOT / "docs" / guide).read_text(encoding="utf-8")
                ratio = len(text.splitlines()) / len(manual.splitlines())
                self.assertGreaterEqual(ratio, 0.25)
                self.assertLessEqual(ratio, 0.37)
                for snippet in (
                    "pip install zstar", "cd ZStar", "zstar config check",
                    "cd examples/3D_Bulk/SiC", "cp -r run work",
                    "zstar bec pre --stru STRU", "zstar bec run", "zstar bec post",
                    "zstar spectra pre --root spectra --response .",
                    "zstar spectra run --root spectra", "zstar spectra post --root spectra",
                    "zstar skill install", f"docs/{guide}",
                ):
                    self.assertIn(snippet, text)
                self.assertNotIn("--calculator abacus", text)
                self.assertNotIn("cd zstar\n", text)

    def test_homepages_preserve_core_scope_results_and_validation_figures(self):
        for name in ("README.md", "README.zh-CN.md"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for snippet in (
                    "Unified", "BEC/APT", "--dim", "q_GAPT", "7.440", "5.394",
                    "CP2K", "VASP", "Quantum ESPRESSO", "zstar piezo",
                    "LO-TO", "PYATB", "Slurm", "Torque", "Specified", "Current",
                    "Global", "--pp", "--orb", "4.18", "8.35", "zstar data db/qnep",
                    r"Z^*_{\kappa,\alpha\beta}",
                ):
                    self.assertIn(snippet, text)
                for image in (
                    "unified_workflow.png", "Figure_10_Spectroscopy_four_dimensions.png",
                    "dielectric_response_examples.png", "unified_efficiency_benchmarks.png",
                    "potential_examples_2d.png",
                ):
                    path = f"docs/paper_figures/{image}"
                    self.assertIn(path, text)
                    self.assertTrue((ROOT / path).is_file())

    def test_sic_agent_prompts_install_the_current_skill_from_github_first(self):
        pages = (
            "README.md", "README.zh-CN.md", "README_PYPI.md",
            "docs/README.md", "docs/README.zh-CN.md",
            "docs/user_guide.md", "docs/user_guide.zh-CN.md",
            "docs/agent_skill.md", "docs/agent_skill.zh-CN.md",
        )
        skill_path = "zstar/agent_skills/zstar-workflows"
        example_path = "examples/3D_Bulk/SiC"
        self.assertIn("name: zstar-workflows", (ROOT / skill_path / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / example_path / "run" / "STRU").is_file())
        for name in pages:
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertNotIn("run-zstar-workflows", text)
                prompts = re.findall(r"^```text\n(.*?)^```$", text, re.M | re.S)
                prompt = next(p for p in prompts if skill_path in p and example_path in p)
                self.assertIn("https://github.com/xdzhu/ZStar", prompt)
                self.assertLess(prompt.index(skill_path), prompt.index(example_path))

    def test_full_guides_preserve_results_and_local_images(self):
        for name in ("user_guide.md", "user_guide.zh-CN.md"):
            with self.subTest(name=name):
                path = ROOT / "docs" / name
                text = path.read_text(encoding="utf-8")
                self.assertGreater(len(text.splitlines()), 750)
                for snippet in ("773", "7.440", "5.394", "q_GAPT", "CP2K", "VASP",
                                "PYATB", "Slurm", "Torque", "zstar-workflows"):
                    self.assertIn(snippet, text)
                parser = LocalImageParser()
                parser.feed(text)
                for source in parser.sources:
                    url = urlsplit(source)
                    if not url.scheme and not url.netloc:
                        self.assertTrue((path.parent / unquote(url.path)).is_file(), source)

    def test_pdf_renderer_reads_full_guides_relative_to_their_directory(self):
        renderer = (ROOT / "docs" / "render_readme_pdfs.mjs").read_text(encoding="utf-8")
        for guide, pdf in (("user_guide.md", "README.en.pdf"),
                           ("user_guide.zh-CN.md", "README.zh-CN.pdf")):
            self.assertIn(f'["docs/{guide}", "docs/{pdf}"', renderer)
        self.assertIn("path.resolve(sourceDirectory, cleanSrc)", renderer)

    def test_documentation_indexes_link_to_full_guides(self):
        for name, guide in (("README.md", "user_guide.md"),
                            ("README.zh-CN.md", "user_guide.zh-CN.md")):
            with self.subTest(name=name):
                text = (ROOT / "docs" / name).read_text(encoding="utf-8")
                self.assertIn(f"]({guide})", text)
                self.assertNotIn("cd zstar\n", text)
