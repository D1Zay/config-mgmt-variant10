"""Модульные тесты для инструмента анализа зависимостей."""

import os
import tempfile
import unittest
from src import dep_viz

SAMPLE_APKINDEX = (
    "P:curl\n"
    "V:8.9.1-r0\n"
    "D:so:libcurl.so.4 so:libc.musl-x86_64.so.1 ca-certificates-bundle>=2024\n"
    "p:cmd:curl=8.9.1-r0\n\n"
    "P:libcurl\n"
    "V:8.9.1-r0\n"
    "D:so:libc.musl-x86_64.so.1\n"
    "p:so:libcurl.so.4=4.8.0\n\n"
    "P:musl\n"
    "V:1.2.5-r0\n"
    "D:\n"
    "p:so:libc.musl-x86_64.so.1=1\n\n"
    "P:ca-certificates-bundle\n"
    "V:20240705-r0\n"
    "D:\n"
)


class TestAllStages(unittest.TestCase):
    """Полный набор тестов для Этапов 1–5 (Вариант 10)."""

    def test_valid_url_args(self):
        """Проверка корректных аргументов с URL."""
        parser = dep_viz.build_parser()
        args = parser.parse_args(
            [
                "--package",
                "curl",
                "--repo",
                "https://example.com/APKINDEX.tar.gz",
            ]
        )
        dep_viz.validate_args(args)
        self.assertEqual(args.package, "curl")

    def test_parse_apkindex_graph(self):
        """Проверка извлечения прямых зависимостей из APKINDEX."""
        graph = dep_viz.parse_apkindex_graph(SAMPLE_APKINDEX)
        self.assertEqual(
            graph["curl"], ["libcurl", "musl", "ca-certificates-bundle"]
        )

    def test_dfs_non_recursive_and_filter(self):
        """Проверка нерекурсивного DFS и фильтрации подстроки."""
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("A: B C\nB: D\nC: E\nD:\nE:\n")
            tmp_path = tmp.name
        full_graph = dep_viz.parse_test_repo_graph(tmp_path)
        os.remove(tmp_path)
        sub_filtered = dep_viz.build_dependency_subgraph_dfs(
            full_graph, "A", "B"
        )
        self.assertEqual(set(sub_filtered.keys()), {"A", "C", "E"})

    def test_reverse_dependencies(self):
        """Проверка поиска обратных зависимостей нерекурсивным DFS."""
        graph = {
            "A": ["B", "C"],
            "B": ["D", "E"],
            "C": ["E"],
            "D": [],
            "E": ["G"],
            "G": [],
        }
        rev_g = dep_viz.find_reverse_dependencies(graph, "G", "")
        self.assertEqual(set(rev_g), {"E", "B", "C", "A"})

    def test_generate_d2_diagram(self):
        """Проверка генерации описания графа на языке диаграмм D2."""
        subgraph = {"A": ["B", "C"], "B": [], "C": []}
        d2_code = dep_viz.generate_d2_diagram(subgraph)
        self.assertIn("direction: down", d2_code)
        self.assertIn('"A" -> "B"', d2_code)
        self.assertIn('"A" -> "C"', d2_code)
        url = dep_viz.build_web_diagram_url(d2_code)
        self.assertTrue(url.startswith(dep_viz.KROKI_D2_URL))


if __name__ == "__main__":
    unittest.main()