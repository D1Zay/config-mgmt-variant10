"""Модульные тесты для инструмента анализа зависимостей."""

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


class TestStage1And2(unittest.TestCase):
    """Тестирование конфигурации (Этап 1) и парсинга APKINDEX (Этап 2)."""

    def test_valid_url_args(self):
        """Проверка корректных аргументов с URL."""
        parser = dep_viz.build_parser()
        args = parser.parse_args(
            ["--package", "curl", "--repo", "https://example.com/APKINDEX.tar.gz"]
        )
        dep_viz.validate_args(args)
        self.assertEqual(args.package, "curl")

    def test_empty_package_error(self):
        """Проверка ошибки при пустом имени пакета."""
        parser = dep_viz.build_parser()
        args = parser.parse_args(
            ["--package", "   ", "--repo", "https://example.com"]
        )
        with self.assertRaises(ValueError):
            dep_viz.validate_args(args)

    def test_missing_test_file_error(self):
        """Проверка ошибки при отсутствии файла тестового репозитория."""
        parser = dep_viz.build_parser()
        args = parser.parse_args(
            ["--package", "A", "--repo", "no_file.txt", "--test-repo"]
        )
        with self.assertRaises(FileNotFoundError):
            dep_viz.validate_args(args)

    def test_parse_apkindex_graph(self):
        """Проверка извлечения прямых зависимостей из APKINDEX."""
        graph = dep_viz.parse_apkindex_graph(SAMPLE_APKINDEX)
        self.assertIn("curl", graph)
        expected = ["libcurl", "musl", "ca-certificates-bundle"]
        self.assertEqual(graph["curl"], expected)
        self.assertEqual(graph["libcurl"], ["musl"])


if __name__ == "__main__":
    unittest.main()