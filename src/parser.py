import os
import hashlib
from typing import Dict, Any, Optional
import logging
from docx import Document
from pypdf import PdfReader
import io

class FileParser:
    """Parser for different file types to extract text content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            self.logger.error(f"Error generating hash for {file_path}: {e}")
            return ""
            
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic file information"""
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'hash': self.get_file_hash(file_path)
            }
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            return {}
            
    def parse_docx(self, file_path: str) -> Optional[str]:
        """Parse DOCX file and extract text"""
        try:
            doc = Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text)
        except Exception as e:
            self.logger.error(f"Error parsing DOCX file {file_path}: {e}")
            return None
            
    def parse_pdf(self, file_path: str) -> Optional[str]:
        """Parse PDF file and extract text"""
        try:
            text = []
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
        except Exception as e:
            self.logger.error(f"Error parsing PDF file {file_path}: {e}")
            return None
            
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse file based on its extension"""
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {}
            
        file_info = self.get_file_info(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        result = {
            'file_path': file_path,
            'file_size': file_info.get('size', 0),
            'content_hash': file_info.get('hash', ''),
            'file_type': file_extension,
            'content': None,
            'parsed_successfully': False
        }
        
        try:
            if file_extension == '.docx':
                content = self.parse_docx(file_path)
            elif file_extension == '.pdf':
                content = self.parse_pdf(file_path)
            else:
                self.logger.warning(f"Unsupported file type: {file_extension}")
                return result
                
            if content:
                result['content'] = content
                result['parsed_successfully'] = True
                self.logger.info(f"Successfully parsed {file_path}")
            else:
                self.logger.warning(f"Failed to extract content from {file_path}")
                
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
            
        return result 