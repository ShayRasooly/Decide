import os
import shutil
import yaml
from src.parser import FileParser
from src.database import DatabaseManager

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

def test_local_e2e_pipeline():
    CONFIG['regex_extractor_enabled'] = True
    CONFIG['openai_extractor_enabled'] = True
    db_path = os.path.join(os.getcwd(), 'local_e2e_test.db')
    verdicts_dir = os.path.join(os.getcwd(), 'verdicts_all')
    output_file = CONFIG.get('real_e2e_output_file', 'real_e2e_output.txt')
    
    if os.path.exists(db_path):
        os.remove(db_path)
    
    parser = FileParser()
    db = DatabaseManager(db_path=db_path)
    verdict_ids = []
    processed_files = []
    regex_total_score = 0
    openai_total_score = 0
    for filename in os.listdir(verdicts_dir):
        file_path = os.path.join(verdicts_dir, filename)
        if not os.path.isfile(file_path):
            continue
        if not (filename.lower().endswith('.docx') or filename.lower().endswith('.pdf') or filename.lower().endswith('.doc')):
            continue
        parse_result = parser.parse_file(file_path)
        processed_files.append(file_path)
        if parse_result.get('parsed_successfully'):
            verdict_id = db.insert_verdict(
                filename=filename,
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
        else:
            print(f"Failed to parse: {file_path}")
        # Score tracking
        regex_score = parse_result.get('extractor_scores', {}).get('regex', 0)
        openai_score = parse_result.get('extractor_scores', {}).get('openai', 0)
        regex_total_score += regex_score
        openai_total_score += openai_score
    # Print extractor scores
    print(f"\nRegex extractor total score: {regex_total_score}")
    print(f"OpenAI extractor total score: {openai_total_score}")
    print(f"Regex extractor goal reached: {regex_total_score >= 15300}")
    print(f"OpenAI extractor goal reached: {openai_total_score >= 15300}")
    # Write summary output
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"\nLocal E2E: Number of files processed: {len(processed_files)}\n")
        f.write(f"Processed files: {processed_files}\n")
        for verdict_id in verdict_ids:
            verdict = db.get_verdict_by_id(verdict_id)
            parsed_content = db.get_parsed_content(verdict_id)
            print('Verdict from DB:', verdict, flush=True)
            print('Parsed Content from DB:', parsed_content, flush=True)
            f.write(f"Verdict from DB: {verdict}\n")
            f.write(f"Parsed Content from DB: {parsed_content}\n")
    print(f"\nLocal E2E: Number of files processed: {len(processed_files)}")
    print(f"Processed files: {processed_files}") 