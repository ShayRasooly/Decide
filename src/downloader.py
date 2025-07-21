import os
import time
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import urllib.parse
import re
from requests.exceptions import RequestException
import yaml

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml'), 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

class VerdictDownloader:
    """Enhanced downloader for verdict files with database integration"""
    
    def __init__(self, download_dir: Optional[str] = None, max_files: Optional[int] = None):
        # Ensure download_dir is always a string
        if download_dir is None:
            download_dir = str(CONFIG.get('download_dir', 'verdicts_all'))
        else:
            download_dir = str(download_dir)
        # Ensure max_files is always an int
        if max_files is None:
            max_files = int(CONFIG.get('max_files', 10))
        else:
            max_files = int(max_files)
        self.download_dir = download_dir
        self.max_files = max_files
        self.logger = logging.getLogger(__name__)
        self._ensure_download_directory()
        self.website_url = CONFIG.get('website_url') or ''
        self.user_agent = CONFIG.get('user_agent', 'Mozilla/5.0')
        self.referer = CONFIG.get('referer', '')
        self.allow_duplicates = CONFIG.get('allow_duplicates', False)
        self.enable_paging = CONFIG.get('enable_paging', True)
        
    def _ensure_download_directory(self):
        """Ensure download directory exists"""
        os.makedirs(self.download_dir, exist_ok=True)
        
    def _sanitize_filename(self, url: str) -> str:
        """Sanitize filename for Windows compatibility"""
        raw_filename = os.path.basename(url.split('?')[0])
        decoded_filename = urllib.parse.unquote(raw_filename)
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', decoded_filename)
        return safe_filename
        
    def _download_file(self, url: str, filename: str) -> Dict[str, Any]:
        """Download a single file with proper error handling"""
        file_path = os.path.join(self.download_dir, filename)
        
        try:
            session = requests.Session()
            headers = {
                "User-Agent": self.user_agent,
                "Referer": self.referer
            }
            
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
            file_size = os.path.getsize(file_path)
            
            return {
                'success': True,
                'file_path': file_path,
                'file_size': file_size,
                'filename': filename,
                'url': url
            }
            
        except RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
            
    def download_verdicts(self, max_files: Optional[int] = None) -> List[Dict[str, Any]]:
        """Download verdict files from the government website, supporting pagination via skip parameter."""
        if max_files is None:
            max_files = self.max_files
        else:
            max_files = int(max_files)
        self.logger.info(f"Starting download of up to {max_files} verdict files (with pagination)")
        downloaded_files = []
        skip = 0
        page_size = 20  # Guess: number of results per page; adjust if needed
        total_downloaded = 0
        driver = None
        try:
            while total_downloaded < max_files:
                if self.enable_paging:
                    paged_url = re.sub(r"skip=\d+", f"skip={skip}", self.website_url)
                else:
                    paged_url = re.sub(r"skip=\d+", "skip=0", self.website_url)
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                driver.get(paged_url)
                time.sleep(5)
                page_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/BlobFolder/']")
                new_links = []
                new_filenames = []
                for link in page_links:
                    url = link.get_attribute("href")
                    if not url:
                        continue
                    filename = self._sanitize_filename(url)
                    file_path = os.path.join(self.download_dir, filename)
                    if not self.allow_duplicates and os.path.exists(file_path):
                        self.logger.info(f"File already exists, skipping: {file_path}")
                        continue
                    new_links.append(link)
                    new_filenames.append(filename)
                if not self.allow_duplicates and not new_links:
                    self.logger.info("All files on this page already exist. Stopping pagination to avoid infinite loop.")
                    break
                for link in new_links:
                    url = link.get_attribute("href")
                    if not url:
                        continue
                    filename = self._sanitize_filename(url)
                    self.logger.info(f"Downloading file {total_downloaded+1}/{max_files}: {filename}")
                    result = self._download_file(url, filename)
                    downloaded_files.append(result)
                    total_downloaded += 1
                    time.sleep(1)
                driver.quit()
                driver = None
                if self.enable_paging:
                    skip += page_size
            return downloaded_files
        except Exception as e:
            self.logger.error(f"Error during download process: {e}")
            return downloaded_files
        finally:
            if driver:
                driver.quit()
                
    def get_download_stats(self, downloaded_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about downloaded files"""
        if not downloaded_files:
            return {}
            
        successful_downloads = [f for f in downloaded_files if f.get('success', False)]
        failed_downloads = [f for f in downloaded_files if not f.get('success', False)]
        
        total_size = sum(f.get('file_size', 0) for f in successful_downloads)
        
        return {
            'total_files': len(downloaded_files),
            'successful_downloads': len(successful_downloads),
            'failed_downloads': len(failed_downloads),
            'success_rate': len(successful_downloads) / len(downloaded_files) if downloaded_files else 0,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }

    def download_first_verdict(self) -> dict:
        """Download only the first verdict file and return result dict."""
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            driver.get(self.website_url)
            time.sleep(5)
            verdict_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/BlobFolder/']")
            if verdict_links:
                url = verdict_links[0].get_attribute("href")
                if url:
                    filename = self._sanitize_filename(url)
                    file_path = os.path.join(self.download_dir, filename)
                    try:
                        session = requests.Session()
                        for cookie in driver.get_cookies():
                            session.cookies.set(cookie['name'], cookie['value'])
                        headers = {
                            "User-Agent": self.user_agent,
                            "Referer": self.referer
                        }
                        response = session.get(url, headers=headers)
                        response.raise_for_status()
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        self.logger.info(f"Saved {file_path}")
                        file_size = os.path.getsize(file_path)
                        return {
                            'success': True,
                            'file_path': file_path,
                            'file_size': file_size,
                            'filename': filename,
                            'url': url
                        }
                    except RequestException as e:
                        self.logger.error(f"Failed to download {url}: {e}")
                        return {'success': False, 'error': str(e), 'url': url}
                    except Exception as e:
                        self.logger.error(f"Failed to download {url}: {e}")
                        return {'success': False, 'error': str(e), 'url': url}
                else:
                    self.logger.warning("First verdict link does not have a valid href.")
                    return {'success': False, 'error': 'No valid href', 'url': None}
            else:
                self.logger.warning("No verdict files found.")
                return {'success': False, 'error': 'No verdict files found', 'url': None}
        finally:
            if driver:
                driver.quit() 