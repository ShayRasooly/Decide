import pytest
import os
import tempfile
import shutil
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