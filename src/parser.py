import os
import hashlib
from typing import Dict, Any, Optional
import logging
from docx import Document
from pypdf import PdfReader
import io
import yaml
import re

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# --- Regex patterns for field extraction ---
REGEX_PATTERNS = {
    'case_number': r'(?:תיק|מספר\s*תיק|מספר|תיק\s*מספר)[:\s]*([\d\-\/]+)',
    'date': r'(\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{2} [א-ת]{3,9} \d{4})',
    'court': r'(בית[\s\S]{0,30}דין|ביה"ד[\s\S]{0,30}|בית המשפט[\s\S]{0,30})',
    'title': r'^(.*?)(?:\n|$)',
    'parties': r'(?:בין[\s\S]{0,100}לבין[\s\S]{0,100})|(?:התובע[\s\S]{0,100}הנתבע[\s\S]{0,100})',
    'judges': r'(?:הרכב|אב"ד|דיינים|דיין|שופט(?:ים)?|לפני)[:\s]*([\u0590-\u05FF\s,\-]+)',
    'law_references': r'(חוק[\u0590-\u05FF\s\d\-]+|סעיף[\u0590-\u05FF\s\d\-]+)',
    'decision_type': r'(פסק[\s\S]{0,10}דין|החלטה|צו|ערעור|בקשה)',
    'location': r'(?:בבית[\s\S]{0,20}דין[\s\S]{0,20})([\u0590-\u05FF\s]+)',
    'verdict_summary': r'(?:סיכום|תקציר|תמצית)[:\s]*([\s\S]{0,500})',
    'lawyers': r'(?:עו"ד|בא\-כח|ב"כ)[:\s]*([\u0590-\u05FF\s,\-]+)',
    'respondents': r'(?:המשיב(?:ים)?|הנתבע(?:ים)?)[:\s]*([\u0590-\u05FF\s,\-]+)',
    'petitioners': r'(?:המבקש(?:ים)?|התובע(?:ים)?)[:\s]*([\u0590-\u05FF\s,\-]+)',
    'court_section': r'(?:מדור|מחלקה|אגף)[:\s]*([\u0590-\u05FF\s]+)',
}

REGEX_ALTERNATIVES = {
    'case_number': [
        r'מספר\s*תיק[:\s]*([\d\-\/]+)',
        r'תיק\s*מספר[:\s]*([\d\-\/]+)'
    ],
    'date': [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2} [א-ת]{3,9} \d{4})'
    ],
    'court': [
        r'(בית המשפט[\s\S]{0,30})'
    ],
    'parties': [
        r'(התובע[\s\S]{0,100}הנתבע[\s\S]{0,100})'
    ]
}

REGEX_ALTERNATIVES.update({
    'verdict_summary': [r'(סיכום|תקציר|תמצית)[\s\S]{0,500}'],
    'lawyers': [r'(עו"ד|בא\-כח|ב"כ)[\s\S]{0,100}'],
    'respondents': [r'(המשיב(?:ים)?|הנתבע(?:ים)?)[\s\S]{0,100}'],
    'petitioners': [r'(המבקש(?:ים)?|התובע(?:ים)?)[\s\S]{0,100}'],
    'court_section': [r'(מדור|מחלקה|אגף)[\s\S]{0,100}'],
})

HEBREW_FIELD_SYNONYMS = {
    'respondents': ['respondents', 'נתבעים', 'הנתבעים', 'המשיבים', 'משיבים'],
    'petitioners': ['petitioners', 'תובעים', 'התובעים', 'המבקשים', 'מבקשים'],
    'lawyers': ['lawyers', 'עו"ד', 'ב"כ', 'בא-כח'],
    'judges': ['judges', 'דיינים', 'שופטים', 'אב"ד', 'דיין'],
}

class FileParser:
    """Parser for different file types to extract text content and fields"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = CONFIG
        self.feature_flags = {
            'regex': self.config.get('regex_extractor_enabled', False),
            'openai': self.config.get('openai_extractor_enabled', False),
            'azure': self.config.get('azure_extractor_enabled', False),
            'google': self.config.get('google_extractor_enabled', False),
            'huggingface': self.config.get('huggingface_extractor_enabled', False),
        }
    
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

    def normalize_fields(self, fields: dict) -> dict:
        """Normalize field names and merge synonyms"""
        normalized = {}
        for key, value in fields.items():
            found = False
            for norm, synonyms in HEBREW_FIELD_SYNONYMS.items():
                if key in synonyms:
                    if norm not in normalized:
                        normalized[norm] = [] if isinstance(value, list) else ''
                    if isinstance(value, list):
                        normalized[norm].extend(value)
                    else:
                        normalized[norm] += value
                    found = True
                    break
            if not found:
                normalized[key] = value
        # Deduplicate lists
        for k, v in normalized.items():
            if isinstance(v, list):
                normalized[k] = list(dict.fromkeys(v))
        return normalized

    def extract_fields_regex(self, content: str) -> Dict[str, Any]:
        """Extract fields using regex patterns and post-process results, with fallbacks and normalization"""
        fields = {}
        for field, pattern in REGEX_PATTERNS.items():
            match = re.search(pattern, content, re.MULTILINE)
            value = None
            if match:
                value = match.group(1).strip()
            elif field in REGEX_ALTERNATIVES:
                for alt_pattern in REGEX_ALTERNATIVES[field]:
                    alt_match = re.search(alt_pattern, content, re.MULTILINE)
                    if alt_match:
                        value = alt_match.group(1).strip()
                        break
            if value:
                # Post-process for specific fields
                if field in ('judges', 'law_references', 'lawyers', 'respondents', 'petitioners'):
                    items = re.split(r'[\n,\-]+', value)
                    items = [item.strip() for item in items if item.strip()]
                    fields[field] = list(dict.fromkeys(items))
                else:
                    fields[field] = value
        return self.normalize_fields(fields)

    def extract_fields_openai(self, content: str) -> Dict[str, Any]:
        """Simulated OpenAI-based extraction for test loop (replace with real API later)"""
        # Simulate extracting 10 law-related fields per file
        return {
            'case_number': '12345',
            'date': '2023-01-01',
            'court': 'בית הדין',
            'title': 'פסק דין',
            'parties': ['פלוני', 'אלמוני'],
            'judges': ['שופט א', 'שופט ב'],
            'law_references': ['חוק X', 'סעיף Y'],
            'decision_type': 'פסק דין',
            'location': 'תל אביב',
            'verdict_summary': 'סיכום פסק הדין',
        }

    def extract_fields_azure(self, content: str) -> Dict[str, Any]:
        """Stub for Azure-based extraction (to be implemented)"""
        # TODO: Integrate Azure AI API
        return {}

    def extract_fields_google(self, content: str) -> Dict[str, Any]:
        """Stub for Google-based extraction (to be implemented)"""
        # TODO: Integrate Google AI API
        return {}

    def extract_fields_huggingface(self, content: str) -> Dict[str, Any]:
        """Stub for HuggingFace-based extraction (to be implemented)"""
        # TODO: Integrate HuggingFace API
        return {}

    def score_fields(self, fields: Dict[str, Any]) -> int:
        """Score based on number of non-empty fields extracted"""
        return sum(1 for v in fields.values() if v)

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse file based on its extension and extract fields using enabled extractors"""
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
            'parsed_successfully': False,
            'fields': {},
            'extractor_scores': {},
            'best_extractor': None,
            'best_score': 0
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
                # Try all enabled extractors and score them
                extractors = []
                if self.feature_flags['regex']:
                    extractors.append(('regex', self.extract_fields_regex))
                if self.feature_flags['openai']:
                    extractors.append(('openai', self.extract_fields_openai))
                if self.feature_flags['azure']:
                    extractors.append(('azure', self.extract_fields_azure))
                if self.feature_flags['google']:
                    extractors.append(('google', self.extract_fields_google))
                if self.feature_flags['huggingface']:
                    extractors.append(('huggingface', self.extract_fields_huggingface))
                best_score = 0
                best_extractor = None
                best_fields = {}
                for name, extractor in extractors:
                    fields = extractor(content)
                    score = self.score_fields(fields)
                    result['extractor_scores'][name] = score
                    if score > best_score:
                        best_score = score
                        best_extractor = name
                        best_fields = fields
                result['fields'] = best_fields
                result['best_extractor'] = best_extractor
                result['best_score'] = best_score
                self.logger.info(f"Successfully parsed {file_path} with best extractor: {best_extractor} (score={best_score})")
            else:
                self.logger.warning(f"Failed to extract content from {file_path}")
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
        return result 