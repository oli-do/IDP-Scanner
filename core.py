import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Queue

from bs4 import BeautifulSoup, Tag
from nicegui import app


def get_languages(soup: BeautifulSoup):
    langs = []
    for tag in soup.find_all():
        if 'xml:lang' in tag.attrs:
            if not tag.attrs['xml:lang'] == 'en':
                langs.append(tag.attrs['xml:lang'])
    return list(set(langs))


def find_error(file_path: str, file_q: Queue, preset: str):
    file_path = os.path.normpath(file_path)
    file_q.put_nowait(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        file = f.read()
    soup = BeautifulSoup(file, 'lxml-xml')
    langs = get_languages(soup)
    if preset == 'exclude latin':
        if 'la' in langs:
            return None
    elif preset == 'greek only':
        if len(langs) == 1 and langs[0] == 'grc':
            pass
        else:
            return None
    text_blocks = soup.find_all('ab')
    issue_pattern = r'[a-zA-Z0-9\*]+'
    issues = []
    forbidden = []
    for block in text_blocks:
        forbidden.append(re.findall(issue_pattern, block.text))
    if forbidden:
        lines = file.splitlines()
        for i in range(len(lines)):
            line = lines[i]
            if not '<lb' in line:
                continue
            line_soup = BeautifulSoup(f'<root>{line}</root>', 'lxml-xml')
            for element in line_soup.find_all():
                if element:
                    if isinstance(element, Tag):
                        try:
                            name = element.name.lower()
                        except AttributeError:
                            continue
                        if name in ['note', 'num'] or 'desc' in name:
                            element.decompose()
            forbidden = re.findall(issue_pattern, line_soup.text)
            if forbidden:
                shortened_file_path = file_path.replace(app.storage.general['idp_data_path'] + os.path.sep, '')
                issues.append({'forbidden': forbidden, 'xml': line, 'line': i, 'file_path': shortened_file_path})
    return issues


def find_errors(files: list, progress_q: Queue, file_q: Queue):
    max_workers = os.cpu_count()
    results = []
    finished = 0
    if 'preset' in app.storage.general:
        preset = app.storage.general['preset'].lower()
    else:
        preset = 'exclude latin'
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(find_error, file, file_q, preset) for file in files]
        for future in as_completed(futures):
            finished += 1
            progress_q.put_nowait(finished / len(files))
            result = future.result()
            if result:
                results.append(result)
    file_q.put('Finalizing...')
    return [r for res in results for r in res]


def init(files, progress_q: Queue, file_q: Queue):
    return find_errors(files, progress_q, file_q)
