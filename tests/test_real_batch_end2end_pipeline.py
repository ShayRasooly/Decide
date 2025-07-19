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

def test_real_batch_end2end_pipeline():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    try:
        # Download multiple real verdicts
        batch_size = int(CONFIG.get('batch_size', 3))
        download_dir = temp_dir  # Always use temp_dir for test isolation
        downloader = VerdictDownloader(download_dir=download_dir, max_files=batch_size)
        results = downloader.download_verdicts(max_files=batch_size)
        downloaded_files = [r['file_path'] for r in results if r['success']]
        num_files = len(downloaded_files)
        assert num_files > 0
        print(f"Downloaded files: {downloaded_files}")
        print(f"Number of files processed: {num_files}")

        parser = FileParser()
        db = DatabaseManager(db_path=db_path)
        verdict_ids = []
        for file_path in downloaded_files:
            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 0
            parse_result = parser.parse_file(file_path)
            assert parse_result['parsed_successfully']
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
            verdict_ids.append(verdict_id)

        # Read from DB and print
        output_file = CONFIG.get('real_e2e_output_file', 'real_e2e_output.txt')
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\nNumber of files processed: {num_files}\n")
            f.write(f"Downloaded files: {downloaded_files}\n")
            for verdict_id in verdict_ids:
                verdict = db.get_verdict_by_id(verdict_id)
                parsed_content = db.get_parsed_content(verdict_id)
                print('Verdict from DB:', verdict, flush=True)
                print('Parsed Content from DB:', parsed_content, flush=True)
                f.write(f"Verdict from DB: {verdict}\n")
                f.write(f"Parsed Content from DB: {parsed_content}\n")
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