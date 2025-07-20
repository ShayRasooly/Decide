import os
import tempfile
import shutil
import yaml
import json
from src.downloader import VerdictDownloader
from src.parser import FileParser
from src.database import DatabaseManager
from src.extractor import AIExtractor

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

def test_real_batch_end2end_pipeline():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    # Backup and modify config.yaml
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        original_config = f.read()
    config = yaml.safe_load(original_config)
    config['store_file_content'] = False
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, allow_unicode=True)
    # Truncate output file at the start of the test
    output_file = config.get('real_e2e_output_file', 'real_e2e_output.txt')
    if os.path.exists(output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.truncate(0)
    try:
        # Download multiple real verdicts
        batch_size = 5  # Force download of 5 files for pattern analysis
        download_dir = temp_dir  # Always use temp_dir for test isolation
        downloader = VerdictDownloader(download_dir=download_dir, max_files=batch_size)
        results = downloader.download_verdicts(max_files=batch_size)
        downloaded_files = [r['file_path'] for r in results if r['success']]
        num_files = len(downloaded_files)
        assert num_files > 0
        print(f"Downloaded files: {downloaded_files}")
        print(f"Number of files processed: {num_files}")

        parser = FileParser()
        extractor = AIExtractor()
        db = DatabaseManager(db_path=db_path, config=config)
        verdict_ids = []
        for file_path in downloaded_files:
            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 0
            parse_result = parser.parse_file(file_path)
            assert parse_result['parsed_successfully']
            # Debug: Print first 10 lines of content
            content_lines = parse_result['content'].split('\n')
            print(f"First 10 lines of content for {file_path}:")
            for i, line in enumerate(content_lines[:10]):
                print(f"  {i+1}: {line}")
            print("--- End of preview ---")
            print(f"Parsed content for {file_path}: {parse_result['content'][:100]}...")
            verdict_id = db.insert_verdict(
                filename=os.path.basename(file_path),
                file_path=file_path,
                file_size=parse_result['file_size'],
                file_type=parse_result['file_type'],
                content_hash=parse_result['content_hash']
            )
            db.insert_parsed_content(
                verdict_id=verdict_id,
                content_type='full_text',
                content=parse_result['content']
            )
            # Extract structured data using AI
            if parse_result.get('file_type') == 'docx':
                extracted_data = extractor.extract_verdict_data(file_path, parse_result['content'])
                print(f"Extracted data dict for {file_path}: {extracted_data}")
                db.insert_extracted_data(
                    verdict_id=verdict_id,
                    extraction_type='structured_data',
                    extracted_data=json.dumps(extracted_data, ensure_ascii=False),
                    confidence_score=extracted_data.get('confidence_score', 0.0)
                )
                print(f"Extracted data for {file_path}: {extracted_data}", flush=True)
            verdict_ids.append(verdict_id)
        # Read from DB and print
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\nNumber of files processed: {num_files}\n")
            f.write(f"Downloaded files: {downloaded_files}\n")
            for verdict_id in verdict_ids:
                verdict = db.get_verdict_by_id(verdict_id)
                parsed_content = db.get_parsed_content(verdict_id)
                extracted_data = db.get_extracted_data(verdict_id)
                print('Verdict from DB:', verdict, flush=True)
                print('Parsed Content from DB:', parsed_content, flush=True)
                print('Extracted Data from DB:', extracted_data, flush=True)
                f.write(f"Verdict from DB: {verdict}\n")
                f.write(f"Parsed Content from DB: {parsed_content}\n")
                f.write(f"Extracted Data from DB: {extracted_data}\n")
    finally:
        # Restore original config.yaml
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(original_config)
        # Explicitly delete the db object and close any open connections
        try:
            del db
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.close()
        except Exception:
            pass
        import gc
        gc.collect()
        shutil.rmtree(temp_dir) 