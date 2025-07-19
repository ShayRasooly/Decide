import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from src.downloader import VerdictDownloader

class TestVerdictDownloader:
    """Test cases for VerdictDownloader class"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def downloader(self, temp_dir):
        """Create a VerdictDownloader instance for testing"""
        return VerdictDownloader(download_dir=temp_dir, max_files=5)
        
    def test_init_creates_download_directory(self, temp_dir):
        """Test that downloader creates download directory"""
        downloader = VerdictDownloader(download_dir=temp_dir)
        assert os.path.exists(temp_dir)
        
    def test_sanitize_filename(self, downloader):
        """Test filename sanitization"""
        # Test URL with special characters
        url = "https://example.com/file%20with%20spaces.docx"
        filename = downloader._sanitize_filename(url)
        assert filename == "file with spaces.docx"
        
        # Test URL with Hebrew characters
        url = "https://example.com/פס%22ד.docx"
        filename = downloader._sanitize_filename(url)
        assert filename == 'פס_ד.docx'
        
        # Test URL with query parameters
        url = "https://example.com/file.docx?param=value"
        filename = downloader._sanitize_filename(url)
        assert filename == "file.docx"
        
    @patch('requests.Session')
    def test_download_file_success(self, mock_session, downloader):
        """Test successful file download"""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"test file content"
        mock_session.return_value.get.return_value = mock_response
        
        url = "https://example.com/test.docx"
        filename = "test.docx"
        
        result = downloader._download_file(url, filename)
        
        assert result['success'] is True
        assert result['filename'] == filename
        assert result['file_size'] > 0
        assert os.path.exists(result['file_path'])
        
    @patch('requests.Session')
    def test_download_file_failure(self, mock_session, downloader):
        """Test failed file download"""
        # Mock failed response
        mock_session.return_value.get.side_effect = Exception("Network error")
        
        url = "https://example.com/test.docx"
        filename = "test.docx"
        
        result = downloader._download_file(url, filename)
        
        assert result['success'] is False
        assert 'error' in result
        assert not os.path.exists(os.path.join(downloader.download_dir, filename))
        
    @patch('selenium.webdriver.Chrome')
    def test_download_verdicts_no_links(self, mock_driver, downloader):
        """Test download when no links are found"""
        # Mock empty page
        mock_element = Mock()
        mock_element.get_attribute.return_value = None
        mock_driver.return_value.find_elements.return_value = []
        
        result = downloader.download_verdicts(max_files=3)
        
        assert result == []
        
    @patch('selenium.webdriver.Chrome')
    @patch('requests.Session')
    def test_download_verdicts_with_links(self, mock_session, mock_driver, downloader):
        """Test download with found links"""
        # Mock successful download
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"test content"
        mock_session.return_value.get.return_value = mock_response
        
        # Mock link elements
        mock_link1 = Mock()
        mock_link1.get_attribute.return_value = "https://example.com/file1.docx"
        mock_link2 = Mock()
        mock_link2.get_attribute.return_value = "https://example.com/file2.pdf"
        
        mock_driver.return_value.find_elements.return_value = [mock_link1, mock_link2]
        
        result = downloader.download_verdicts(max_files=2)
        
        assert len(result) == 2
        assert all(r['success'] for r in result)
        
    def test_get_download_stats(self, downloader):
        """Test download statistics calculation"""
        # Mock download results
        downloaded_files = [
            {'success': True, 'file_size': 1024, 'filename': 'file1.docx'},
            {'success': True, 'file_size': 2048, 'filename': 'file2.pdf'},
            {'success': False, 'error': 'Network error', 'filename': 'file3.docx'}
        ]
        
        stats = downloader.get_download_stats(downloaded_files)
        
        assert stats['total_files'] == 3
        assert stats['successful_downloads'] == 2
        assert stats['failed_downloads'] == 1
        assert stats['success_rate'] == 2/3
        assert stats['total_size_bytes'] == 3072
        assert stats['total_size_mb'] == 0.0  # Less than 1MB
        
    def test_get_download_stats_empty(self, downloader):
        """Test download statistics with empty results"""
        stats = downloader.get_download_stats([])
        
        assert stats == {}
        
    def test_max_files_limit(self, downloader):
        """Test that max_files limit is respected"""
        assert downloader.max_files == 5
        
        # Test with custom max_files
        downloader.max_files = 10
        assert downloader.max_files == 10 