import os
import tempfile
import shutil
import yaml
from src.downloader import VerdictDownloader
from src.parser import FileParser
from src.database import DatabaseManager

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

def test_real_end2end_pipeline():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    try:
        # Download a real verdict
        download_dir = temp_dir  # Always use temp_dir for test isolation
        downloader = VerdictDownloader(download_dir=download_dir, max_files=1)
        result = downloader.download_first_verdict()
        assert result['success'] is True
        file_path = result['file_path']
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 0
        print(f"Downloaded file: {file_path}")

        # Parse the real file
        parser = FileParser()
        parse_result = parser.parse_file(file_path)
        assert parse_result['parsed_successfully']
        print(f"Parsed content: {parse_result['content'][:100]}...")

        # Store in DB
        db = DatabaseManager(db_path=db_path)
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

        # Read from DB and print
        verdict = db.get_verdict_by_id(verdict_id)
        parsed_content = db.get_parsed_content(verdict_id)
        print('Verdict from DB:', verdict, flush=True)
        print('Parsed Content from DB:', parsed_content, flush=True)
        # Write output to persistent file
        with open(CONFIG.get('real_e2e_output_file', 'real_e2e_output.txt'), 'a', encoding='utf-8') as f:
            f.write('Verdict from DB: ' + str(verdict) + '\n')
            f.write('Parsed Content from DB: ' + str(parsed_content) + '\n')
    finally:
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