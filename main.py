#!/usr/bin/env python3
"""
Main application for the verdict analysis pipeline.
Downloads files, parses them, stores in database, and runs analytics.
"""

import logging
import os
import sys
from typing import List, Dict, Any
import json
from datetime import datetime
import yaml

# Load configuration
with open(os.path.join(os.path.dirname(__file__), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.downloader import VerdictDownloader
from src.parser import FileParser
from src.database import DatabaseManager
from src.analytics import AnalyticsEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class VerdictAnalysisPipeline:
    """Main pipeline for downloading, parsing, and analyzing verdict files"""
    
    def __init__(self, download_dir: str = None, max_files: int = None):
        self.config = CONFIG
        self.downloader = VerdictDownloader(
            download_dir=download_dir or self.config.get('download_dir', 'downloads'),
            max_files=max_files or self.config.get('max_files', 10)
        )
        self.parser = FileParser()
        self.db = DatabaseManager()
        self.analytics = AnalyticsEngine()
        self.logger = logging.getLogger(__name__)
        
    def run_pipeline(self, max_files: int = None) -> Dict[str, Any]:
        """Run the complete pipeline"""
        self.logger.info("Starting verdict analysis pipeline")
        
        # Step 1: Download files
        self.logger.info("Step 1: Downloading verdict files")
        downloaded_files = self.downloader.download_verdicts(max_files=max_files or self.config.get('max_files', 10))
        
        if not downloaded_files:
            self.logger.warning("No files downloaded")
            return {'status': 'no_files_downloaded'}
            
        # Step 2: Parse files and store in database
        self.logger.info("Step 2: Parsing files and storing in database")
        parsed_results = []
        
        for download_result in downloaded_files:
            if not download_result.get('success', False):
                continue
                
            file_path = download_result['file_path']
            filename = download_result['filename']
            
            # Parse the file
            parse_result = self.parser.parse_file(file_path)
            
            if parse_result:
                # Store in database
                verdict_id = self.db.insert_verdict(
                    filename=filename,
                    file_path=file_path,
                    file_size=parse_result.get('file_size'),
                    file_type=parse_result.get('file_type'),
                    content_hash=parse_result.get('content_hash')
                )
                
                # Store parsed content
                if parse_result.get('content'):
                    self.db.insert_parsed_content(
                        verdict_id=verdict_id,
                        content_type='full_text',
                        content=parse_result['content']
                    )
                    
                parsed_results.append({
                    'verdict_id': verdict_id,
                    'parse_result': parse_result,
                    'download_result': download_result
                })
                
        # Step 3: Run analytics
        self.logger.info("Step 3: Running analytics")
        analytics_results = []
        
        for parsed_result in parsed_results:
            content = parsed_result['parse_result'].get('content')
            if content:
                analysis = self.analytics.generate_comprehensive_analysis(content)
                analytics_results.append(analysis)
                
                # Store analytics in database
                self.db.insert_analytics(
                    analysis_type='comprehensive',
                    analysis_data=json.dumps(analysis, ensure_ascii=False)
                )
                
        # Step 4: Generate reports
        self.logger.info("Step 4: Generating reports")
        report_file = self.config.get('e2e_output_file', 'analysis_report.txt')
        report = self.analytics.generate_report(analytics_results)
        
        # Save report to file
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        # Get database statistics
        db_stats = self.db.get_download_stats()
        download_stats = self.downloader.get_download_stats(downloaded_files)
        
        # Final summary
        summary = {
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'download_stats': download_stats,
            'database_stats': db_stats,
            'files_processed': len(parsed_results),
            'analytics_generated': len(analytics_results),
            'report_file': report_file
        }
        
        self.logger.info("Pipeline completed successfully")
        return summary
        
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the system"""
        db_stats = self.db.get_download_stats()
        file_type_stats = self.db.get_file_type_stats()
        
        return {
            'database_stats': db_stats,
            'file_type_distribution': file_type_stats,
            'download_directory': self.downloader.download_dir,
            'database_path': self.db.db_path
        }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verdict Analysis Pipeline')
    parser.add_argument('--max-files', type=int, default=CONFIG.get('max_files', 10), 
                       help='Maximum number of files to download')
    parser.add_argument('--download-dir', type=str, default=CONFIG.get('download_dir', 'downloads'),
                       help='Directory to store downloaded files')
    parser.add_argument('--status', action='store_true',
                       help='Show current system status')
    
    args = parser.parse_args()
    
    pipeline = VerdictAnalysisPipeline(
        download_dir=args.download_dir,
        max_files=args.max_files
    )
    
    if args.status:
        status = pipeline.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        result = pipeline.run_pipeline(max_files=args.max_files)
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main() 