import pytest
from unittest.mock import patch, MagicMock
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import tempfile

# Assuming webscraper.py is in the same directory or accessible in PYTHONPATH
from webscraper import fetch_docker_best_practices, update_rules

# --- Fixtures ---

@pytest.fixture
def mock_successful_response():
    """Mocks a successful requests.get() response with sample HTML."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.content = b'''
    <html>
        <body>
            <main>
                <h2>Rule 1 Title</h2>
                <p>Description for rule 1. It might have characters (") that need cleaning.</p>
                <p>And a second paragraph for rule 1.</p>
                <h3>Sub-Rule 1.1 Title</h3>
                <p>Description for sub-rule 1.1. Also "gosu" might be mentioned.</p>
                <h2>Rule 2 Title</h2>
                <p>Description for rule 2.\nThis has a newline.</p>
            </main>
        </body>
    </html>
    '''
    mock_resp.raise_for_status = MagicMock() # Does nothing for status_code 200
    return mock_resp

@pytest.fixture
def mock_http_error_response():
    """Mocks a requests.get() response that will raise an HTTPError."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 404
    mock_resp.content = b"Not Found"
    mock_resp.raise_for_status = MagicMock(side_effect=requests.exceptions.HTTPError("404 Client Error"))
    return mock_resp

@pytest.fixture
def mock_html_no_main():
    """Mocks HTML content without a <main> tag."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.content = b'''
    <html><body><div>No main tag here.</div></body></html>
    '''
    mock_resp.raise_for_status = MagicMock()
    return mock_resp

@pytest.fixture
def mock_html_no_headings():
    """Mocks HTML content with a <main> tag but no h2/h3 headings."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.content = b'''
    <html><body><main><p>Some text but no headings.</p></main></body></html>
    '''
    mock_resp.raise_for_status = MagicMock()
    return mock_resp

# --- Tests for fetch_docker_best_practices ---

@patch('webscraper.requests.get')
def test_fetch_successful_with_valid_content(mock_get, mock_successful_response):
    """Test successful fetching and parsing of practices."""
    mock_get.return_value = mock_successful_response
    
    practices = fetch_docker_best_practices()
    
    assert practices is not None
    assert len(practices) == 3 # Rule 1, Sub-Rule 1.1, Rule 2
    
    assert practices[0]['title'] == "Rule 1 Title"
    assert practices[0]['description'] == r"Description for rule 1. It might have characters (\") that need cleaning. And a second paragraph for rule 1."
    
    assert practices[1]['title'] == "Sub-Rule 1.1 Title"
    assert practices[1]['description'] == r"Description for sub-rule 1.1. Also \"gosu\" might be mentioned." # Escaped quotes around gosu

    assert practices[2]['title'] == "Rule 2 Title"
    assert practices[2]['description'] == "Description for rule 2. This has a newline." # Newline replaced by space by the scraper

    mock_get.assert_called_once_with("https://docs.docker.com/develop/dev-best-practices/")

@patch('webscraper.requests.get')
def test_fetch_handles_requests_exception(mock_get):
    """Test handling of a generic requests.exceptions.RequestException."""
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    
    with patch('webscraper.print') as mock_print: # To check the error message
        practices = fetch_docker_best_practices()
        assert practices is None
        mock_print.assert_called_once_with("Error fetching Docker best practices: Network error")

@patch('webscraper.requests.get')
def test_fetch_handles_http_error(mock_get, mock_http_error_response):
    """Test handling of an HTTPError (e.g., 404)."""
    mock_get.return_value = mock_http_error_response
    
    with patch('webscraper.print') as mock_print:
        practices = fetch_docker_best_practices()
        assert practices is None
        mock_print.assert_called_once_with("Error fetching Docker best practices: 404 Client Error")

@patch('webscraper.requests.get')
def test_fetch_handles_missing_main_content(mock_get, mock_html_no_main):
    """Test handling when HTML is missing the <main> tag."""
    mock_get.return_value = mock_html_no_main
    
    with patch('webscraper.print') as mock_print:
        practices = fetch_docker_best_practices()
        assert practices is None
        mock_print.assert_called_once_with("Error fetching Docker best practices: Could not find main content section")

@patch('webscraper.requests.get')
def test_fetch_handles_no_headings_found(mock_get, mock_html_no_headings):
    """Test handling when <main> tag exists but contains no h2/h3 headings."""
    mock_get.return_value = mock_html_no_headings
    
    practices = fetch_docker_best_practices()
    assert practices is not None
    assert len(practices) == 0 # Should return an empty list

# --- Tests for update_rules ---

@patch('webscraper.fetch_docker_best_practices')
def test_update_rules_successful(mock_fetch, tmp_path):
    """Test successful update_rules: fetches practices and saves them."""
    sample_practices = [{"title": "Test Rule", "description": "Test Desc"}]
    mock_fetch.return_value = sample_practices
    
    config_dir = tmp_path # tmp_path is a pytest fixture providing a Path object to a temp dir
    
    result = update_rules(config_dir)
    assert result is True
    
    expected_file = config_dir / "docker_best_practices.json"
    assert expected_file.exists()
    
    with open(expected_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    assert saved_data == sample_practices
    mock_fetch.assert_called_once()

@patch('webscraper.fetch_docker_best_practices')
def test_update_rules_fetch_fails(mock_fetch, tmp_path):
    """Test update_rules when fetching practices fails."""
    mock_fetch.return_value = None
    config_dir = tmp_path
    
    result = update_rules(config_dir)
    assert result is False
    
    expected_file = config_dir / "docker_best_practices.json"
    assert not expected_file.exists() # File should not be created
    mock_fetch.assert_called_once()

@patch('webscraper.fetch_docker_best_practices')
@patch('webscraper.open', side_effect=IOError("Disk full")) # Mock open to simulate save error
@patch('webscraper.print') # To check error message
def test_update_rules_save_fails(mock_print_ws, mock_open, mock_fetch, tmp_path):
    """Test update_rules when saving the JSON file fails."""
    sample_practices = [{"title": "Test Rule", "description": "Test Desc"}]
    mock_fetch.return_value = sample_practices
    config_dir = tmp_path
    
    result = update_rules(config_dir)
    assert result is False
    mock_fetch.assert_called_once()
    mock_open.assert_called_once_with(config_dir / "docker_best_practices.json", "w", encoding='utf-8')
    mock_print_ws.assert_called_once_with("Error saving practices: Disk full") 