#!/usr/bin/env python3
"""
Debug script to test the AIExtractor with test content
"""

import sys
import os
import re
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.extractor import AIExtractor

def test_extractor():
    """Test the extractor with sample content"""
    extractor = AIExtractor()
    
    # Test content from the test file - exact copy
    sample_content = """
        בית המשפט המחוזי בתל אביב
        כבוד השופט דוד כהן
        תיק 12345/23
        בין התובע: ישראל ישראלי
        לבין הנתבע: משה כהן
        תאריך: 15/12/2023
        """
    
    print("Testing extractor with sample content:")
    print("Content:", repr(sample_content))
    print("Content lines:")
    for i, line in enumerate(sample_content.split('\n')):
        print(f"  Line {i}: {repr(line)}")
    print()
    
    # Test individual extraction methods
    print("Testing court name extraction:")
    court_name = extractor._extract_court_name(sample_content)
    print(f"Extracted court name: {repr(court_name)}")
    print()
    
    print("Testing judge name extraction:")
    judge_name = extractor._extract_judge_name(sample_content)
    print(f"Extracted judge name: {repr(judge_name)}")
    print()
    
    print("Testing verdict ID extraction:")
    verdict_id = extractor._extract_verdict_id(sample_content)
    print(f"Extracted verdict ID: {repr(verdict_id)}")
    print()
    
    print("Testing verdict date extraction:")
    verdict_date = extractor._extract_verdict_date(sample_content)
    print(f"Extracted verdict date: {repr(verdict_date)}")
    print()
    
    print("Testing parties extraction:")
    parties = extractor._extract_parties(sample_content)
    print(f"Extracted parties: {repr(parties)}")
    print()
    
    # Test regex patterns directly
    print("Testing regex patterns directly:")
    judge_pattern = re.compile('\\s+כבוד השופט(?:ת)?\\s+[^\\n]+', re.IGNORECASE | re.MULTILINE)
    match = judge_pattern.search(sample_content)
    print(f"Judge pattern match: {match.group(0) if match else 'None'}")
    
    case_pattern = re.compile('\\s+תיק\\s+([\\d\\/-]+)', re.IGNORECASE)
    match = case_pattern.search(sample_content)
    print(f"Case pattern match: {match.group(1) if match else 'None'}")
    
    date_pattern = re.compile('\\s+תאריך:\\s*(\\d{1,2}/\\d{1,2}/\\d{4})', re.IGNORECASE)
    match = date_pattern.search(sample_content)
    print(f"Date pattern match: {match.group(1) if match else 'None'}")
    print()
    
    # Test full extraction
    print("Testing full extraction:")
    result = extractor.extract_verdict_data("test.docx", sample_content)
    print("Full result:", result)

if __name__ == "__main__":
    test_extractor() 