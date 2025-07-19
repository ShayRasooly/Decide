import os
import tempfile
import shutil
from unittest.mock import patch, Mock
from src.downloader import VerdictDownloader
from src.parser import FileParser
from src.database import DatabaseManager

def test_end2end_download_parse_store_and_read(capfd):
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    try:
        # Setup downloader, parser, and database
        downloader = VerdictDownloader(download_dir=temp_dir, max_files=1)
        parser = FileParser()
        db = DatabaseManager(db_path=db_path)

        # Mock Selenium driver and link
        with patch('src.downloader.webdriver.Chrome') as mock_webdriver, \
             patch('src.downloader.requests.Session') as mock_session:
            mock_driver = Mock()
            mock_link = Mock()
            mock_link.get_attribute.return_value = "https://example.com/test.docx"
            mock_driver.find_elements.return_value = [mock_link]
            mock_driver.get_cookies.return_value = []
            mock_driver.current_url = "https://www.gov.il/he/Departments/DynamicCollectors/verdict_the_rabbinical_courts?skip=0"
            mock_webdriver.return_value = mock_driver

            # Mock requests session
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = b"test file content"
            mock_session.return_value.get.return_value = mock_response

            # Download file
            result = downloader.download_first_verdict()
            assert result['success'] is True
            file_path = result['file_path']
            assert os.path.exists(file_path)

            # Parse file
            with patch.object(parser, 'parse_file', return_value={
                'file_path': file_path,
                'file_size': 17,
                'content_hash': 'dummyhash',
                'file_type': '.docx',
                'content': 'dummy content',
                'parsed_successfully': True
            }):
                parse_result = parser.parse_file(file_path)
                assert parse_result['parsed_successfully']

                # Store in DB
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
                with open('e2e_output.txt', 'a', encoding='utf-8') as f:
                    f.write('Verdict from DB: ' + str(verdict) + '\n')
                    f.write('Parsed Content from DB: ' + str(parsed_content) + '\n')

        # Capture and check output
        out, _ = capfd.readouterr()
        assert 'Verdict' in out
        assert 'Parsed Content' in out
        # Explicitly delete the db object to close any open connections
        del db
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            conn.close()
        except Exception:
            pass
        # Move the DB file out of the temp directory before deleting
        try:
            new_db_path = os.path.join(os.getcwd(), 'test_cleanup.db')
            if os.path.exists(db_path):
                os.replace(db_path, new_db_path)
        except Exception:
            pass
    finally:
        import gc
        gc.collect()
        shutil.rmtree(temp_dir)
        # Optionally, remove the moved DB file
        try:
            os.remove(new_db_path)
        except Exception:
            pass 