# Verdict Analysis Pipeline

A comprehensive test infrastructure for downloading, parsing, storing, and analyzing legal verdict documents from government websites.

## Features

- **Automated Download**: Downloads verdict files from government websites using Selenium
- **File Parsing**: Extracts text content from DOCX and PDF files
- **Database Storage**: SQLite database for storing file metadata and parsed content
- **Analytics Engine**: Text analysis, legal term detection, and document structure analysis
- **Comprehensive Testing**: Unit tests with pytest and coverage reporting
- **Logging**: Detailed logging for debugging and monitoring

## Project Structure

```
Decide/
├── src/                    # Source code modules
│   ├── downloader.py      # File download functionality
│   ├── parser.py          # File parsing and text extraction
│   ├── database.py        # Database operations
│   └── analytics.py       # Text analysis and reporting
├── tests/                 # Test files
│   ├── test_downloader.py # Downloader tests
│   └── test_parser.py     # Parser tests
├── downloads/             # Downloaded files (gitignored)
├── data/                  # Database files (gitignored)
├── main.py               # Main application
├── requirements.txt       # Python dependencies
├── pytest.ini           # Test configuration
└── README.md            # This file
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Chrome/Chromium** (required for Selenium WebDriver)

## Usage

### Basic Pipeline Execution

Run the complete pipeline to download, parse, and analyze verdict files:

```bash
python main.py --max-files 5
```

### Check System Status

View current database statistics and file distribution:

```bash
python main.py --status
```

### Custom Configuration

```bash
python main.py --max-files 10 --download-dir custom_downloads
```

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only  
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Database Schema

### Tables

1. **verdicts**: Stores file metadata
   - id, filename, file_path, file_size, download_date, file_type, content_hash, status

2. **parsed_content**: Stores extracted text content
   - id, verdict_id, content_type, content, parsed_date

3. **analytics**: Stores analysis results
   - id, analysis_type, analysis_data, created_date

## Analytics Features

- **Text Statistics**: Word count, sentence count, paragraph analysis
- **Legal Term Detection**: Hebrew legal terminology analysis
- **Document Structure**: Formatting and structure analysis
- **Comparative Analysis**: Multi-document comparison
- **Report Generation**: Human-readable analysis reports

## Configuration

### Environment Variables

Create a `.env` file for custom configuration:

```env
DOWNLOAD_DIR=downloads
MAX_FILES=10
DATABASE_PATH=data/verdicts.db
LOG_LEVEL=INFO
```

### Logging

Logs are written to:
- Console output
- `pipeline.log` file

## Error Handling

The pipeline includes comprehensive error handling for:
- Network failures during download
- File parsing errors
- Database connection issues
- Invalid file formats

## Performance Considerations

- Downloads are rate-limited to avoid overwhelming the server
- File parsing is optimized for large documents
- Database operations use connection pooling
- Analytics are cached to avoid redundant processing

## Contributing

1. Write tests for new features
2. Ensure all tests pass: `pytest`
3. Check code coverage: `pytest --cov=src`
4. Follow PEP 8 style guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.
