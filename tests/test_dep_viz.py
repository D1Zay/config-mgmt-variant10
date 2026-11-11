"""Модульные тесты для инструмента анализа зависимостей."""

import os
import tempfile
import unittest
from src import dep_viz


class TestStage1Config(unittest.TestCase):
    """Тестирование конфигурации и обработки ошибок Этапа 1."""

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

    def test_valid_test_repo_file(self):
        """Проверка успешной валидации существующего тестового файла."""
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("A: B C\n")
            tmp_path = tmp.name
        parser = dep_viz.build_parser()
        args = parser.parse_args(
            ["--package", "A", "--repo", tmp_path, "--test-repo"]
        )
        dep_viz.validate_args(args)
        os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()