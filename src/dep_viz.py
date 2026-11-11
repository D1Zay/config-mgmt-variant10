"""Модуль визуализации графа зависимостей пакетов Alpine Linux (apk)."""

import argparse
import os
import sys

EXIT_ERROR_CODE = 1
MIN_STR_LEN = 0
HTTP_PREFIX = "http://"
HTTPS_PREFIX = "https://"


def build_parser():
    """Создает и настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов (Вариант 10)."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Имя анализируемого пакета.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="URL-адрес репозитория или путь к файлу тестового репозитория.",
    )
    parser.add_argument(
        "--test-repo",
        action="store_true",
        help="Режим работы с тестовым репозиторием.",
    )
    parser.add_argument(
        "--filter",
        default="",
        help="Подстрока для фильтрации пакетов.",
    )
    return parser


def is_valid_url(url_str):
    """Проверяет, начинается ли строка с допустимого HTTP префикса."""
    return url_str.startswith(HTTP_PREFIX) or url_str.startswith(HTTPS_PREFIX)


def validate_args(args):
    """Проверяет корректность переданных пользователем параметров."""
    pkg_clean = args.package.strip()
    repo_clean = args.repo.strip()
    if len(pkg_clean) == MIN_STR_LEN:
        raise ValueError("Имя пакета не может быть пустым.")
    if len(repo_clean) == MIN_STR_LEN:
        raise ValueError("Путь или URL репозитория не может быть пустым.")
    if args.test_repo:
        if not os.path.isfile(repo_clean):
            raise FileNotFoundError(
                f"Файл тестового репозитория не найден: {repo_clean}"
            )
    else:
        if not is_valid_url(repo_clean) and not os.path.isfile(repo_clean):
            raise ValueError(
                "Репозиторий должен быть корректным HTTP/HTTPS URL или файлом."
            )


def print_config_params(args):
    """Выводит все настраиваемые параметры в формате ключ-значение."""
    print(f"package={args.package}")
    print(f"repo={args.repo}")
    print(f"test_repo={args.test_repo}")
    print(f"filter={args.filter}")


def main(argv=None):
    """Основная точка входа приложения."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
    except (ValueError, FileNotFoundError) as err:
        print(f"Ошибка конфигурации: {err}", file=sys.stderr)
        sys.exit(EXIT_ERROR_CODE)
    print_config_params(args)


if __name__ == "__main__":
    main()