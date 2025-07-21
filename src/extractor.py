#!/usr/bin/env python3
"""
AI-powered data extraction module for verdict documents.
Extracts structured data from DOCX files including verdict ID, court name, judge name, etc.
"""

import os
import logging
import json
import re
from typing import Dict, Any, Optional, List, Tuple
import yaml
from datetime import datetime
from docx import Document

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

class AIExtractor:
    """AI-powered extractor for structured data from verdict documents"""
    
    def __init__(self, debug_output_path: Optional[str] = None) -> None:
        print(f"AIExtractor __init__ called with debug_output_path={debug_output_path}")
        self.logger = logging.getLogger(__name__)
        
        # Load patterns from configuration
        extractor_config = CONFIG.get('extractor_patterns', {})
        self.use_ai = CONFIG.get('extractor_use_ai', False)
        self.debug_output_path = debug_output_path
        self.debug_enabled = CONFIG.get('extractor_debug_output', False)
        self.ner_pipeline = None
        if self.use_ai:
            try:
                from transformers import pipeline  # type: ignore
                self.ner_pipeline = pipeline("ner", model="avichr/heBERT_NER", aggregation_strategy="simple")  # type: ignore
            except Exception as e:
                print(f"WARNING: Could not load AI NER model: {e}. Falling back to regex extraction.")
                self.use_ai = False
        print(f"AIExtractor config: use_ai={self.use_ai}, debug_enabled={self.debug_enabled}")
        
        # Compile regex patterns for better performance
        self.court_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                              for pattern in extractor_config.get('court_patterns', [])]
        self.judge_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                              for pattern in extractor_config.get('judge_patterns', [])]
        self.case_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                             for pattern in extractor_config.get('case_patterns', [])]
        self.date_patterns = [re.compile(pattern, re.MULTILINE) 
                             for pattern in extractor_config.get('date_patterns', [])]
        self.party_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                              for pattern in extractor_config.get('party_patterns', [])]
        self.verdict_type_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                                     for pattern in extractor_config.get('verdict_type_patterns', [])]
        
        # Load keywords for fallback extraction
        self.court_keywords = extractor_config.get('court_keywords', [])
        self.judge_keywords = extractor_config.get('judge_keywords', [])
        self.case_keywords = extractor_config.get('case_keywords', [])
        self.date_keywords = extractor_config.get('date_keywords', [])
        self.party_keywords = extractor_config.get('party_keywords', [])
        self.verdict_type_keywords = extractor_config.get('verdict_type_keywords', [])
        
        # Performance settings
        self.max_lines_to_scan = extractor_config.get('max_lines_to_scan', 20)
        self.confidence_threshold = CONFIG.get('extractor_confidence_threshold', 0.7)
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate that all required patterns and keywords are loaded"""
        required_patterns = [
            'court_patterns', 'judge_patterns', 'case_patterns',
            'date_patterns', 'party_patterns', 'verdict_type_patterns'
        ]
        required_keywords = [
            'court_keywords', 'judge_keywords', 'case_keywords',
            'date_keywords', 'party_keywords', 'verdict_type_keywords'
        ]
        
        for pattern_name in required_patterns:
            if not getattr(self, pattern_name):
                self.logger.warning(f"Missing {pattern_name} in configuration")
        
        for keyword_name in required_keywords:
            if not getattr(self, keyword_name):
                self.logger.warning(f"Missing {keyword_name} in configuration")
    
    def extract_verdict_data(self, file_path: str, content: str) -> Dict[str, Any]:
        print(f"extract_verdict_data called for {file_path}, self.use_ai={self.use_ai}")
        if self.use_ai and self.ner_pipeline is not None:
            print("extract_verdict_data: use_ai=True, dispatching to _extract_with_ai")
            return self._extract_with_ai(file_path, content)
        print("extract_verdict_data: using regex extraction")
        try:
            # Early termination for empty content
            if not content or not content.strip():
                self.logger.warning("Empty content provided for extraction")
                return self._create_empty_result()
            
            lines = content.split('\n')
            self.logger.info(f"Attempting to extract data from {len(lines)} lines")
            self.logger.info(f"First 5 lines: {lines[:5]}")

            # Strategy 1: Try regex extraction
            court_name = self._extract_court_name(content)
            judge_name = self._extract_judge_name(content)
            verdict_id = self._extract_verdict_id(content)
            
            # Strategy 2: Fallback to line-by-line search (limited to max_lines_to_scan)
            if not court_name:
                court_name = self._find_court_in_lines(lines)
            if not judge_name:
                judge_name = self._find_judge_in_lines(lines)
            if not verdict_id:
                verdict_id = self._find_case_in_lines(lines)
            
            verdict_date = self._extract_verdict_date(content)
            if not verdict_date:
                verdict_date = self._find_date_in_lines(lines)
            parties = self._extract_parties(content)
            if not parties:
                parties = self._find_parties_in_lines(lines)
            verdict_type = self._extract_verdict_type(content)
            if not verdict_type:
                verdict_type = self._find_verdict_type_in_lines(lines)

            # Always build the data dictionary with whatever values are found
            data = {
                'verdict_id': verdict_id,
                'court_name': court_name,
                'judge_name': judge_name,
                'case_number': verdict_id,  # Same as verdict_id for now
                'verdict_date': verdict_date,
                'parties': parties,
                'verdict_type': verdict_type,
                'confidence_score': 0.0,  # Will be set below
                'extraction_timestamp': datetime.now().isoformat(),
                'file_path': file_path
            }
            # Validate and clean the result
            data = self._validate_and_clean_result(data)
            data['confidence_score'] = self._calculate_confidence(data)
            self.logger.info(f"Extraction completed. Found {len([v for v in data.values() if v])} fields")
            return data
        except Exception as e:
            self.logger.error(f"Error during extraction: {str(e)}")
            return self._create_empty_result()
    
    def _validate_and_clean_field(self, value: Optional[str], field_name: str) -> Optional[str]:
        """
        Validate and clean an extracted field
        
        Args:
            value: The extracted value
            field_name: Name of the field for logging
            
        Returns:
            Cleaned and validated value or None if invalid
        """
        if not value:
            return None
        
        # Clean the value
        cleaned = value.strip()
        
        # Basic validation
        if len(cleaned) < 2:
            self.logger.warning(f"Field {field_name} too short: '{cleaned}'")
            return None
        
        if len(cleaned) > 500:
            self.logger.warning(f"Field {field_name} too long: {len(cleaned)} chars")
            return cleaned[:500]
        
        return cleaned
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create an empty result structure"""
        return {
            'verdict_id': None,
            'court_name': None,
            'judge_name': None,
            'case_number': None,
            'verdict_date': None,
            'parties': None,
            'verdict_type': None,
            'confidence_score': 0.0,
            'extraction_timestamp': datetime.now().isoformat(),
            'file_path': None
        }
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate confidence score based on extracted fields, only considering fields present in the content."""
        # Only count fields that are not None as expected fields
        present_fields = [k for k, v in data.items() if v is not None and k not in ('confidence_score', 'extraction_timestamp', 'file_path')]
        filled_fields = sum(1 for k in present_fields if data[k] is not None and data[k] != '')
        total_fields = len(present_fields)
        print(f"DEBUG: data={data}")
        print(f"DEBUG: present_fields={present_fields}")
        print(f"DEBUG: filled_fields={filled_fields}, total_fields={total_fields}")
        return min(filled_fields / total_fields, 1.0) if total_fields > 0 else 0.0
    
    def _validate_and_clean_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the extracted data"""
        cleaned_data = {}
        for key, value in data.items():
            if value is not None and isinstance(value, str):
                # Clean up whitespace and remove extra characters
                cleaned_value = value.strip()
                if cleaned_value:
                    cleaned_data[key] = cleaned_value
                else:
                    cleaned_data[key] = None
            else:
                cleaned_data[key] = value
        return cleaned_data
    
    def _extract_court_name(self, content: str) -> Optional[str]:
        """Extract court name from content"""
        for pattern in self.court_patterns:
            match = pattern.search(content)
            if match:
                court_text = match.group(0).strip()
                # Clean up by taking only the first line
                lines = court_text.split('\n')
                return lines[0].strip()
        return None
    
    def _extract_judge_name(self, content: str) -> Optional[str]:
        """Extract judge name from content"""
        for pattern in self.judge_patterns:
            match = pattern.search(content)
            if match:
                # Return the full matched line, including after colon
                return match.group(0).strip()
        return None
    
    def _extract_case_number(self, content: str) -> Optional[str]:
        """Extract case number from content"""
        for pattern in self.case_patterns:
            match = pattern.search(content)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_verdict_id(self, content: str) -> Optional[str]:
        """Extract verdict ID from content"""
        for pattern in self.case_patterns:
            match = pattern.search(content)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_verdict_date(self, content: str) -> Optional[str]:
        """Extract verdict date from content"""
        for pattern in self.date_patterns:
            match = pattern.search(content)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_parties(self, content: str) -> Optional[str]:
        """Extract parties from content"""
        for pattern in self.party_patterns:
            match = pattern.search(content)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_verdict_type(self, content: str) -> Optional[str]:
        """Extract verdict type from content"""
        for pattern in self.verdict_type_patterns:
            match = pattern.search(content)
            if match:
                return match.group(0).strip()
        return None
    
    def _find_court_in_lines(self, lines: List[str]) -> Optional[str]:
        """Find court name in lines using keywords"""
        for line in lines[:self.max_lines_to_scan]:
            for keyword in self.court_keywords:
                if keyword in line:
                    # Try to extract the court name after the keyword
                    match = re.search(r'(בית המשפט[^\n]+|בית הדין[^\n]+)', line)
                    if match:
                        return match.group(1).strip()
                    return line.strip()
        return None

    def _find_judge_in_lines(self, lines: List[str]) -> Optional[str]:
        """Find judge name in lines using keywords"""
        for line in lines[:self.max_lines_to_scan]:
            for keyword in self.judge_keywords:
                if keyword in line:
                    # Try to extract the judge name after the keyword
                    match = re.search(r'(כבוד השופט(?:ת)?[^\n]+|כבוד הדיין(?:ים)?[^\n]+|הרב[^\n]+)', line)
                    if match:
                        return match.group(1).strip()
                    return line.strip()
        return None
    
    def _find_case_in_lines(self, lines: List[str]) -> Optional[str]:
        """Find case number in lines using keywords"""
        for line in lines[:self.max_lines_to_scan]:
            for keyword in self.case_keywords:
                if keyword in line:
                    # Try to extract the number using regex
                    match = re.search(r'([\d\/-]+)', line)
                    if match:
                        return match.group(1)
                    # Fallback: return the line
                    return line.strip()
        return None
    
    def _find_date_in_lines(self, lines: List[str]) -> Optional[str]:
        """Find date in lines using keywords and patterns"""
        for line in lines[:self.max_lines_to_scan]:
            # Try date patterns first
            for pattern in self.date_patterns:
                match = pattern.search(line)
                if match:
                    return match.group(1)
            # Try keywords
            for keyword in self.date_keywords:
                if keyword in line:
                    # Try to extract the date using regex
                    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', line)
                    if match:
                        return match.group(1)
                    match = re.search(r'(\d{1,2}-\d{1,2}-\d{4})', line)
                    if match:
                        return match.group(1)
                    match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', line)
                    if match:
                        return match.group(1)
                    # Fallback: return the line
                    return line.strip()
        return None
    
    def _find_parties_in_lines(self, lines: List[str]) -> Optional[str]:
        """Find parties in lines using keywords"""
        for line in lines[:self.max_lines_to_scan]:
            for keyword in self.party_keywords:
                if keyword in line:
                    return line.strip()
        return None
    
    def _find_verdict_type_in_lines(self, lines: List[str]) -> Optional[str]:
        """Find verdict type in lines using keywords"""
        for line in lines[:self.max_lines_to_scan]:
            for keyword in self.verdict_type_keywords:
                if keyword in line:
                    return line.strip()
        return None
    
    def extract_from_docx(self, file_path: str) -> Dict[str, Any]:
        """
        Extract data from DOCX file using python-docx.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Dictionary containing extracted data
        """
        try:
            if not file_path.lower().endswith('.docx'):
                raise ValueError("File is not a DOCX file")
            
            # Load the document
            doc = Document(file_path)
            
            # Extract text content
            content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content.append(paragraph.text.strip())
            
            # Join all text content
            full_content = '\n'.join(content)
            
            # Extract structured data
            return self.extract_verdict_data(file_path, full_content)
            
        except Exception as e:
            self.logger.error(f"Error extracting from DOCX {file_path}: {str(e)}")
            return {
                'error': str(e),
                'confidence_score': 0.0
            }
    
    def extract_from_text(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Extract data from text content.
        
        Args:
            file_path: Path to the source file
            content: Text content to analyze
            
        Returns:
            Dictionary containing extracted data
        """
        return self.extract_verdict_data(file_path, content)
    
    def get_extraction_summary(self, extracted_data: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of extracted data.
        
        Args:
            extracted_data: Extracted data dictionary
            
        Returns:
            Formatted summary string
        """
        if 'error' in extracted_data:
            return f"Extraction failed: {extracted_data['error']}"
        
        summary_parts = []
        
        if extracted_data.get('court_name'):
            summary_parts.append(f"Court: {extracted_data['court_name']}")
        
        if extracted_data.get('judge_name'):
            summary_parts.append(f"Judge: {extracted_data['judge_name']}")
        
        if extracted_data.get('case_number'):
            summary_parts.append(f"Case Number: {extracted_data['case_number']}")
        
        if extracted_data.get('verdict_id'):
            summary_parts.append(f"Verdict ID: {extracted_data['verdict_id']}")
        
        if extracted_data.get('verdict_date'):
            summary_parts.append(f"Date: {extracted_data['verdict_date']}")
        
        if extracted_data.get('parties'):
            parties_str = ', '.join([f"{k}: {v}" for k, v in extracted_data['parties'].items()])
            summary_parts.append(f"Parties: {parties_str}")
        
        summary_parts.append(f"Confidence: {extracted_data.get('confidence_score', 0):.2f}")
        
        return ' | '.join(summary_parts) 

    def _extract_with_ai(self, file_path: str, content: str) -> Dict[str, Any]:
        import os
        print(f"_extract_with_ai called for file: {file_path}")
        print(f"Current working directory: {os.getcwd()}")
        try:
            if self.ner_pipeline is None:
                print("AIExtractor: ner_pipeline is None, returning empty dict")
                return {}
            entities = self.ner_pipeline(content)
            print(f"AIExtractor: entities from NER pipeline: {entities}")
            print(f"Type of entities: {type(entities)}, Length: {len(entities) if hasattr(entities, '__len__') else 'N/A'}")
            debug_line = f"DEBUG: Raw NER entities for {file_path}: {entities}\n"
            print(debug_line)
            print(f"self.debug_enabled: {self.debug_enabled}, self.debug_output_path: {self.debug_output_path}")
            if self.debug_enabled and self.debug_output_path:
                print(f"About to write debug output to {self.debug_output_path} (cwd: {os.getcwd()})")
                try:
                    with open(self.debug_output_path, "a", encoding="utf-8") as f:
                        f.write(debug_line)
                        f.flush()
                except Exception as file_exc:
                    print(f"Exception while writing debug file: {file_exc}")
            # Group entities by label
            entity_map = {}
            for ent in entities:
                label = ent['entity_group']
                if label not in entity_map:
                    entity_map[label] = []
                entity_map[label].append(ent['word'])
            # Map NER labels to our fields (heuristic)
            data = {
                'verdict_id': next((w for w in entity_map.get('MISC', []) if w.isdigit() or '/' in w), None),
                'court_name': next((w for w in entity_map.get('ORG', []) if 'בית' in w or 'דין' in w), None),
                'judge_name': next((w for w in entity_map.get('PER', []) if 'הרב' in w or 'שופט' in w), None),
                'case_number': next((w for w in entity_map.get('MISC', []) if w.isdigit() or '/' in w), None),
                'verdict_date': next((w for w in entity_map.get('DATE', []) if w), None),
                'parties': entity_map.get('PER', []),
                'verdict_type': next((w for w in entity_map.get('MISC', []) if 'פסק' in w or 'החלטה' in w or 'צו' in w), None),
                'confidence_score': 1.0 if entities else 0.0,
                'extraction_timestamp': datetime.now().isoformat(),
                'file_path': file_path
            }
            return data
        except Exception as e:
            self.logger.error(f"Error during AI extraction: {str(e)}")
            return self._create_empty_result() 