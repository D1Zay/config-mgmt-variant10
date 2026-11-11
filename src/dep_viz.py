"""Модуль визуализации графа зависимостей пакетов Alpine Linux (apk)."""

import argparse
import base64
import io
import os
import sys
import tarfile
import urllib.request
import webbrowser
import zlib

EXIT_ERROR_CODE = 1
MIN_STR_LEN = 0
PREFIX_LEN = 2
SPLIT_LIMIT = 1
ZLIB_LEVEL = 9
HTTP_PREFIX = "http://"
HTTPS_PREFIX = "https://"
APKINDEX_ARCHIVE = "APKINDEX.tar.gz"
APKINDEX_ENTRY = "APKINDEX"
VERSION_CHARS = "><=~"
KROKI_D2_URL = "https://kroki.io/d2/svg/"
USER_AGENT_HEADER = "Mozilla/5.0"


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
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Режим вывода обратных зависимостей для заданного пакета.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Скачать изображение графа на ПК и открыть в браузере.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Путь для сохранения файла изображения графа (SVG).",
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


def normalize_apk_url(repo_url):
    """Формирует полный URL до файла APKINDEX.tar.gz."""
    if repo_url.endswith(APKINDEX_ARCHIVE):
        return repo_url
    base = repo_url.rstrip("/")
    return f"{base}/{APKINDEX_ARCHIVE}"


def extract_apkindex_from_bytes(raw_bytes):
    """Извлекает текстовое содержимое файла APKINDEX из tar.gz байтов."""
    bio = io.BytesIO(raw_bytes)
    with tarfile.open(fileobj=bio, mode="r:gz") as tar:
        member = tar.getmember(APKINDEX_ENTRY)
        extracted = tar.extractfile(member)
        if extracted is None:
            raise ValueError("Не удалось прочитать APKINDEX внутри архива.")
        return extracted.read().decode("utf-8", errors="replace")


def fetch_apkindex_text(repo_source):
    """Загружает и распаковывает APKINDEX по URL или локальному пути."""
    if is_valid_url(repo_source):
        target_url = normalize_apk_url(repo_source)
        with urllib.request.urlopen(target_url) as response:
            raw_data = response.read()
        return extract_apkindex_from_bytes(raw_data)
    if repo_source.endswith(".tar.gz"):
        with open(repo_source, "rb") as file_obj:
            raw_data = file_obj.read()
        return extract_apkindex_from_bytes(raw_data)
    with open(repo_source, "r", encoding="utf-8-sig") as file_obj:
        return file_obj.read()


def strip_version_spec(token):
    """Очищает токен зависимости или предоставления от версии и префикса."""
    cleaned = token.lstrip("!")
    for idx, char in enumerate(cleaned):
        if char in VERSION_CHARS:
            return cleaned[:idx]
    return cleaned


def parse_apk_block(block_text):
    """Разбирает один блок пакета из APKINDEX."""
    pkg_name = ""
    raw_deps = []
    provides = []
    for line in block_text.splitlines():
        if line.startswith("P:"):
            pkg_name = line[PREFIX_LEN:].strip()
        elif line.startswith("D:"):
            raw_deps.extend(line[PREFIX_LEN:].strip().split())
        elif line.startswith("p:"):
            provides.extend(line[PREFIX_LEN:].strip().split())
    return pkg_name, raw_deps, provides


def resolve_raw_deps(pkg_name, raw_deps, provides_map):
    """Преобразует сырые токены зависимостей в имена пакетов."""
    resolved = []
    for token in raw_deps:
        if token.startswith("!"):
            continue
        clean_tok = strip_version_spec(token)
        target = provides_map.get(clean_tok, clean_tok)
        if target and target != pkg_name and target not in resolved:
            resolved.append(target)
    return resolved


def parse_apkindex_graph(index_text):
    """Строит граф зависимостей из текста APKINDEX."""
    raw_map = {}
    provides_map = {}
    for block in index_text.split("\n\n"):
        pkg_name, raw_deps, provides = parse_apk_block(block.strip())
        if not pkg_name:
            continue
        raw_map[pkg_name] = raw_deps
        provides_map[pkg_name] = pkg_name
        for prov in provides:
            prov_key = strip_version_spec(prov)
            if prov_key:
                provides_map[prov_key] = pkg_name
    graph = {}
    for pkg_name, raw_deps in raw_map.items():
        graph[pkg_name] = resolve_raw_deps(pkg_name, raw_deps, provides_map)
    return graph


def parse_test_repo_graph(file_path):
    """Читает граф тестового репозитория, где пакеты названы буквами."""
    graph = {}
    with open(file_path, "r", encoding="utf-8-sig") as file_obj:
        for raw_line in file_obj:
            line = raw_line.strip()
            if not line:
                continue
            if ":" in line:
                left, right = line.split(":", SPLIT_LIMIT)
                pkg = left.strip()
                deps = right.replace(",", " ").split()
            else:
                parts = line.split()
                pkg = parts[0]
                deps = parts[SPLIT_LIMIT:]
            graph.setdefault(pkg, [])
            for dep in deps:
                if dep not in graph[pkg]:
                    graph[pkg].append(dep)
                graph.setdefault(dep, [])
    return graph


def is_filtered(pkg_name, filter_substr):
    """Проверяет, должен ли пакет быть исключен по подстроке фильтрации."""
    return bool(filter_substr) and (filter_substr in pkg_name)


def build_dependency_subgraph_dfs(full_graph, start_pkg, filter_substr=""):
    """Строит транзитивный граф зависимостей алгоритмом DFS без рекурсии."""
    if start_pkg not in full_graph:
        raise ValueError(f"Пакет '{start_pkg}' не найден в репозитории.")
    if is_filtered(start_pkg, filter_substr):
        return {}
    subgraph = {}
    visited = set()
    stack = [start_pkg]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        neighbors = full_graph.get(current, [])
        valid_deps = [
            dep for dep in neighbors if not is_filtered(dep, filter_substr)
        ]
        subgraph[current] = valid_deps
        for dep in reversed(valid_deps):
            if dep not in visited:
                stack.append(dep)
    return subgraph


def invert_graph(full_graph):
    """Инвертирует направления ребер графа для поиска обратных зависимостей."""
    inverted = {pkg: [] for pkg in full_graph}
    for pkg, deps in full_graph.items():
        for dep in deps:
            inverted.setdefault(dep, [])
            if pkg not in inverted[dep]:
                inverted[dep].append(pkg)
    return inverted


def find_reverse_dependencies(full_graph, target_pkg, filter_substr=""):
    """Находит все пакеты, зависящие от заданного, через нерекурсивный DFS."""
    if target_pkg not in full_graph:
        raise ValueError(f"Пакет '{target_pkg}' не найден в репозитории.")
    inverted = invert_graph(full_graph)
    rev_subgraph = build_dependency_subgraph_dfs(
        inverted, target_pkg, filter_substr
    )
    return [pkg for pkg in rev_subgraph if pkg != target_pkg]


def print_reverse_dependencies(target_pkg, rev_deps):
    """Выводит на экран список обратных зависимостей пакета."""
    print(f"Обратные зависимости для пакета {target_pkg}:")
    if not rev_deps:
        print("нет")
        return
    for pkg in rev_deps:
        print(f"- {pkg}")


def generate_d2_diagram(subgraph):
    """Формирует текстовое представление графа зависимостей на языке D2."""
    lines = ["direction: down"]
    for pkg, deps in subgraph.items():
        if not deps:
            lines.append(f'"{pkg}"')
        for dep in deps:
            lines.append(f'"{pkg}" -> "{dep}"')
    return "\n".join(lines)


def build_web_diagram_url(d2_text):
    """Кодирует описание D2 в URL для просмотра графа на сайте в браузере."""
    compressed = zlib.compress(d2_text.encode("utf-8"), ZLIB_LEVEL)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return f"{KROKI_D2_URL}{encoded}"


def save_diagram_image(web_url, output_path):
    """Скачивает изображение графа по URL и сохраняет его на компьютер."""
    req = urllib.request.Request(
        web_url, headers={"User-Agent": USER_AGENT_HEADER}
    )
    with urllib.request.urlopen(req) as response:
        img_bytes = response.read()
    with open(output_path, "wb") as file_obj:
        file_obj.write(img_bytes)


def handle_visualization_output(pkg_name, d2_code, args):
    """Обрабатывает вывод D2-кода, скачивание картинки и открытие браузера."""
    print(d2_code)
    if not args.web and not args.output:
        return
    web_url = build_web_diagram_url(d2_code)
    out_file = args.output.strip() if args.output else f"{pkg_name}_graph.svg"
    save_diagram_image(web_url, out_file)
    print(f"\nИзображение сохранено в файл: {os.path.abspath(out_file)}")
    if args.web:
        print(f"Ссылка на граф: {web_url}")
        webbrowser.open(web_url)


def load_repository_graph(args):
    """Загружает граф зависимостей в зависимости от выбранного режима."""
    repo_clean = args.repo.strip()
    if args.test_repo:
        return parse_test_repo_graph(repo_clean)
    index_text = fetch_apkindex_text(repo_clean)
    return parse_apkindex_graph(index_text)


def main(argv=None):
    """Основная точка входа приложения."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
        full_graph = load_repository_graph(args)
        pkg_name = args.package.strip()
        if args.reverse:
            rev_deps = find_reverse_dependencies(
                full_graph, pkg_name, args.filter
            )
            print_reverse_dependencies(pkg_name, rev_deps)
        else:
            subgraph = build_dependency_subgraph_dfs(
                full_graph, pkg_name, args.filter
            )
            d2_code = generate_d2_diagram(subgraph)
            handle_visualization_output(pkg_name, d2_code, args)
    except Exception as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        sys.exit(EXIT_ERROR_CODE)


if __name__ == "__main__":
    main()