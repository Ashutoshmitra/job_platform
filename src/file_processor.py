"""
File processing utilities for handling various file formats and archives.
"""
import os
import json
import csv
import configparser
import xml.etree.ElementTree as ET
import zipfile
import tarfile
import gzip
import shutil
import urllib.parse
import requests
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def get_file_type(file_path: str) -> str:
    """Identifies the file type for parsing or unzipping."""
    if file_path.lower().endswith('.tar.gz'):
        return '.tar.gz'
    _, extension = os.path.splitext(file_path)
    return extension.lower()


def get_parser_for_file(file_path: str) -> tuple:
    """
    Identifies the appropriate Python parser/library for a given file path.
    """
    try:
        if file_path.lower().endswith('.tar.gz'):
            file_extension = '.tar.gz'
        else:
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()
    except (TypeError, AttributeError):
        return None, None

    parser_mapping = {
        # Data Formats
        '.csv': 'csv library (built-in)',
        '.json': 'json library (built-in)',
        '.xml': 'xml.etree.ElementTree (built-in) or lxml library',
        '.yaml': 'PyYAML library',
        '.yml': 'PyYAML library',
        '.ini': 'configparser library (built-in)',
        '.conf': 'configparser library (built-in)',
        '.xls': 'xlrd library or pandas library',
        '.xlsx': 'openpyxl library or pandas library',

        # Document Formats
        '.txt': 'Standard file I/O (open() function)',
        '.md': 'markdown library or mistune library',
        '.pdf': 'PyPDF2 library or pdfplumber library',
        '.docx': 'python-docx library',
        '.doc': 'python-docx library (may have limitations with older .doc formats)',
        '.rtf': 'striprtf library',

        # Image Formats (for metadata or processing)
        '.jpg': 'Pillow (PIL) library',
        '.jpeg': 'Pillow (PIL) library',
        '.png': 'Pillow (PIL) library',
        '.gif': 'Pillow (PIL) library',
        '.bmp': 'Pillow (PIL) library',
        '.tiff': 'Pillow (PIL) library',

        # Compressed Files
        '.zip': 'zipfile library (built-in)',
        '.tar': 'tarfile library (built-in)',
        '.gz': 'gzip library (built-in)',
        '.tar.gz': 'tarfile library (built-in)',
        '.tgz': 'tarfile library (built-in)',
    }

    parser = parser_mapping.get(file_extension, f"Unsupported file type")
    return parser, file_extension


def unzip_file_if_needed(file_path: str, extract_to_dir: str = '.') -> Optional[str]:
    """
    Checks if a file is a compressed archive and extracts it if it is.
    """
    if not os.path.exists(file_path):
        logger.error(f"File '{file_path}' not found.")
        return None

    file_type = get_file_type(file_path)
    archive_types = ['.zip', '.tar', '.gz', '.tar.gz', '.tgz']

    if file_type not in archive_types:
        logger.info(f"'{os.path.basename(file_path)}' is not a recognized compressed file.")
        return None

    file_name = os.path.basename(file_path)
    logger.info(f"Archive detected: '{file_name}'. Extracting...")

    # Create a unique extraction folder name
    extraction_folder_name = file_name.replace('.tar.gz', '').replace('.zip', '').replace('.tgz', '').replace('.gz', '').replace('.tar', '')
    extraction_path = os.path.join(extract_to_dir, extraction_folder_name)

    if not os.path.exists(extraction_path):
        os.makedirs(extraction_path)

    try:
        if file_type == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extraction_path)
        elif file_type in ['.tar', '.tar.gz', '.tgz']:
            with tarfile.open(file_path, 'r:*') as tar_ref:
                tar_ref.extractall(path=extraction_path)
        elif file_type == '.gz':
            output_filename = os.path.join(extraction_path, os.path.splitext(file_name)[0])
            with gzip.open(file_path, 'rb') as f_in:
                with open(output_filename, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

        logger.info(f"Successfully extracted to '{extraction_path}'")
        return extraction_path
    except (zipfile.BadZipFile, tarfile.ReadError, IOError) as e:
        logger.error(f"Error during extraction of '{file_name}': {e}")
        return None


def parse_file_to_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single file (CSV, INI, XML, JSON) and returns its content as a Python dictionary.
    """
    file_type = get_file_type(file_path)
    file_name = os.path.basename(file_path)

    logger.info(f"Parsing '{file_name}'...")

    try:
        if file_type == '.csv':
            with open(file_path, mode='r', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                return [row for row in reader]

        elif file_type == '.ini':
            config = configparser.ConfigParser()
            config.read(file_path)
            return {section: dict(config.items(section)) for section in config.sections()}

        elif file_type == '.xml':
            def element_to_dict(element):
                node = {}
                for child in element:
                    if child.tag not in node:
                        node[child.tag] = element_to_dict(child) if len(child) > 0 else child.text
                    else:
                        # Handle multiple elements with the same tag
                        if not isinstance(node[child.tag], list):
                            node[child.tag] = [node[child.tag]]
                        node[child.tag].append(element_to_dict(child) if len(child) > 0 else child.text)
                return node

            tree = ET.parse(file_path)
            root = tree.getroot()
            return {root.tag: element_to_dict(root)}

        elif file_type == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        else:
            logger.warning(f"Unsupported file type for parsing: {file_type}")
            return None

    except Exception as e:
        logger.error(f"Could not parse '{file_name}'. Error: {e}")
        return None


def process_input(input_path: str, extract_to_dir: str = './temp') -> Dict[str, Any]:
    """
    Processes the input, whether it's a local file path or a URL,
    and returns parsed data from all files found.
    """
    downloaded_file_path = None
    all_parsed_data = {}

    # Ensure extract directory exists
    os.makedirs(extract_to_dir, exist_ok=True)

    # Check if the input is a URL
    if input_path.startswith('http://') or input_path.startswith('https://'):
        logger.info(f"URL detected: {input_path}")
        parsed_url = urllib.parse.urlparse(input_path)
        path = parsed_url.path
        filename = os.path.basename(path) or 'downloaded_file'
        downloaded_file_path = os.path.join(extract_to_dir, filename)

        # Download the file
        logger.info(f"Downloading '{filename}'...")
        try:
            response = requests.get(input_path, stream=True)
            response.raise_for_status()

            with open(downloaded_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Successfully downloaded and saved as '{downloaded_file_path}'")

        except requests.exceptions.RequestException as e:
            logger.error(f"Could not download the file. {e}")
            raise
    else:
        # Treat as a local file path
        logger.info(f"Local file path detected: {input_path}")
        downloaded_file_path = input_path

    # Process the file (extract if needed, then parse)
    if downloaded_file_path and os.path.exists(downloaded_file_path):
        extraction_path = unzip_file_if_needed(downloaded_file_path, extract_to_dir)

        if extraction_path:
            # Parse files inside the extracted archive
            for root, _, files in os.walk(extraction_path):
                for name in files:
                    file_to_parse = os.path.join(root, name)
                    parsed_data = parse_file_to_json(file_to_parse)
                    if parsed_data:
                        all_parsed_data[name] = parsed_data
        else:
            # Parse the file directly
            parsed_data = parse_file_to_json(downloaded_file_path)
            if parsed_data:
                filename = os.path.basename(downloaded_file_path)
                all_parsed_data[filename] = parsed_data

    return all_parsed_data