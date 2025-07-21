import pytest
import os
import tempfile
import shutil
import yaml
from unittest.mock import Mock, patch, MagicMock
from src.downloader import VerdictDownloader

def test_real_verdict_download():
    temp_dir = tempfile.mkdtemp()
    try:
        downloader = VerdictDownloader(download_dir=temp_dir, max_files=1)
        result = downloader.download_first_verdict()
        assert result['success'] is True
        file_path = result['file_path']
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 0
        print(f"Downloaded file: {file_path}")
    finally:
        shutil.rmtree(temp_dir)

def test_infinite_download_duplicate_bug():
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    # Backup config
    with open(config_path, 'r', encoding='utf-8') as f:
        original_config = f.read()
    config = yaml.safe_load(original_config)
    config['allow_duplicates'] = True
    config['enable_paging'] = False
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, allow_unicode=True)
    try:
        downloader = VerdictDownloader(download_dir=temp_dir, max_files=22)
        downloader.enable_paging = False
        downloader.allow_duplicates = True
        results = downloader.download_verdicts(max_files=22)
        filenames = [r['filename'] for r in results if 'filename' in r]
        from collections import Counter
        counts = Counter(filenames)
        duplicates = [fname for fname, count in counts.items() if count > 1]
        assert len(duplicates) > 0, "Expected at least one file to be downloaded more than once when allow_duplicates is True and enable_paging is False."
    finally:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(original_config)
        shutil.rmtree(temp_dir) 