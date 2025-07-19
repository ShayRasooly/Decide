import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from src.parser import FileParser

class TestFileParser:
    """Test cases for FileParser class"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def parser(self):
        """Create a FileParser instance for testing"""
        return FileParser()
        
    def test_get_file_hash(self, parser, temp_dir):
        """Test file hash generation"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test content")
            
        hash_value = parser.get_file_hash(test_file)
        
        assert len(hash_value) == 64  # SHA-256 hash length
        assert hash_value.isalnum()  # Should be alphanumeric
        
    def test_get_file_hash_nonexistent(self, parser):
        """Test hash generation for nonexistent file"""
        hash_value = parser.get_file_hash("nonexistent_file.txt")
        assert hash_value == ""
        
    def test_get_file_info(self, parser, temp_dir):
        """Test file information extraction"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test content")
            
        info = parser.get_file_info(test_file)
        
        assert 'size' in info
        assert 'modified' in info
        assert 'hash' in info
        assert info['size'] > 0
        assert info['hash'] != ""
        
    def test_get_file_info_nonexistent(self, parser):
        """Test file info for nonexistent file"""
        info = parser.get_file_info("nonexistent_file.txt")
        assert info == {}
        
    @patch('src.parser.Document')
    def test_parse_docx_success(self, mock_document, parser, temp_dir):
        """Test successful DOCX parsing"""
        # Mock document with paragraphs
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Second paragraph"
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_document.return_value = mock_doc
        
        test_file = os.path.join(temp_dir, "test.docx")
        # No need to write a file since Document is mocked
        
        result = parser.parse_docx(test_file)
        
        assert result == "First paragraph\nSecond paragraph"
        
    @patch('src.parser.Document')
    def test_parse_docx_failure(self, mock_document, parser, temp_dir):
        """Test DOCX parsing failure"""
        mock_document.side_effect = Exception("Document error")
        
        test_file = os.path.join(temp_dir, "test.docx")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        result = parser.parse_docx(test_file)
        
        assert result is None
        
    @patch('PyPDF2.PdfReader')
    def test_parse_pdf_success(self, mock_pdf_reader, parser, temp_dir):
        """Test successful PDF parsing"""
        # Mock PDF pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "First page content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Second page content"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        test_file = os.path.join(temp_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        result = parser.parse_pdf(test_file)
        
        assert result == "First page content\nSecond page content"
        
    @patch('PyPDF2.PdfReader')
    def test_parse_pdf_failure(self, mock_pdf_reader, parser, temp_dir):
        """Test PDF parsing failure"""
        mock_pdf_reader.side_effect = Exception("PDF error")
        
        test_file = os.path.join(temp_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        result = parser.parse_pdf(test_file)
        
        assert result is None
        
    def test_parse_file_docx(self, parser, temp_dir):
        """Test parsing DOCX file"""
        test_file = os.path.join(temp_dir, "test.docx")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        with patch.object(parser, 'parse_docx', return_value="parsed content"):
            result = parser.parse_file(test_file)
            
        assert result['file_path'] == test_file
        assert result['file_type'] == '.docx'
        assert result['content'] == "parsed content"
        assert result['parsed_successfully'] is True
        assert result['file_size'] > 0
        assert result['content_hash'] != ""
        
    def test_parse_file_pdf(self, parser, temp_dir):
        """Test parsing PDF file"""
        test_file = os.path.join(temp_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        with patch.object(parser, 'parse_pdf', return_value="parsed content"):
            result = parser.parse_file(test_file)
            
        assert result['file_path'] == test_file
        assert result['file_type'] == '.pdf'
        assert result['content'] == "parsed content"
        assert result['parsed_successfully'] is True
        
    def test_parse_file_unsupported_type(self, parser, temp_dir):
        """Test parsing unsupported file type"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        result = parser.parse_file(test_file)
        
        assert result['file_path'] == test_file
        assert result['file_type'] == '.txt'
        assert result['content'] is None
        assert result['parsed_successfully'] is False
        
    def test_parse_file_nonexistent(self, parser):
        """Test parsing nonexistent file"""
        result = parser.parse_file("nonexistent_file.docx")
        
        assert result == {}
        
    def test_parse_file_with_hebrew_content(self, parser, temp_dir):
        """Test parsing file with Hebrew content"""
        test_file = os.path.join(temp_dir, "test.docx")
        with open(test_file, 'w') as f:
            f.write("dummy content")
            
        hebrew_content = "פס\"ד דחיית בקשה לעיון צד ג' על פי צו ביהמ\"ש"
        
        with patch.object(parser, 'parse_docx', return_value=hebrew_content):
            result = parser.parse_file(test_file)
            
        assert result['content'] == hebrew_content
        assert result['parsed_successfully'] is True 