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


class TestStages1To3(unittest.TestCase):
    """Тестирование Этапов 1, 2 и 3."""

    def test_valid_url_args(self):
        """Проверка корректных аргументов с URL."""
        parser = dep_viz.build_parser()
        args = parser.parse_args(
            ["--package", "curl", "--repo", "https://example.com/APKINDEX.tar.gz"]
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
        sub_all = dep_viz.build_dependency_subgraph_dfs(full_graph, "A", "")
        self.assertEqual(set(sub_all.keys()), {"A", "B", "C", "D", "E"})
        sub_filtered = dep_viz.build_dependency_subgraph_dfs(
            full_graph, "A", "B"
        )
        self.assertEqual(set(sub_filtered.keys()), {"A", "C", "E"})

    def test_dfs_cycle_handling(self):
        """Проверка корректной обработки циклических зависимостей."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        sub = dep_viz.build_dependency_subgraph_dfs(graph, "A", "")
        self.assertEqual(set(sub.keys()), {"A", "B", "C"})
        self.assertEqual(sub["C"], ["A"])


if __name__ == "__main__":
    unittest.main()