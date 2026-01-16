#!/usr/bin/env python3
"""
Download PDFs from alislam.org book collection.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://www.alislam.org"
BOOKS_URL = "https://www.alislam.org/books/hazrat-mirza-tahir-ahmad/"
PDF_BASE = "https://files.alislam.cloud/pdf/"
OUTPUT_DIR = Path(__file__).parent / "pdfs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def get_book_pages(url: str) -> list[dict]:
    """Fetch the books listing page and extract individual book page URLs."""
    print(f"Fetching book listing from {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    books = []

    # Find all book links - they typically link to /book/... paths
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/book/" in href or "/library/books/" in href:
            full_url = urljoin(BASE_URL, href)
            title = link.get_text(strip=True) or href.split("/")[-2]
            if full_url not in [b["url"] for b in books]:
                books.append({"title": title, "url": full_url})

    print(f"Found {len(books)} book pages")
    return books


def get_pdf_url(book_page_url: str) -> str | None:
    """Visit a book page and extract the PDF download link."""
    print(f"  Checking {book_page_url}")
    try:
        resp = requests.get(book_page_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching page: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Look for PDF links in various patterns
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if ".pdf" in href.lower():
            return urljoin(BASE_URL, href)

    # Check for files.alislam.cloud pattern in scripts or data attributes
    for script in soup.find_all("script"):
        if script.string and "files.alislam.cloud" in script.string:
            match = re.search(r'https://files\.alislam\.cloud/pdf/[^"\']+\.pdf', script.string)
            if match:
                return match.group(0)

    # Check all text content for PDF URLs
    page_text = str(soup)
    match = re.search(r'https://files\.alislam\.cloud/pdf/[^"\'<>\s]+\.pdf', page_text)
    if match:
        return match.group(0)

    return None


def download_pdf(url: str, output_path: Path) -> bool:
    """Download a PDF file."""
    if output_path.exists():
        print(f"  Already exists: {output_path.name}")
        return True

    print(f"  Downloading {url}")
    try:
        resp = requests.get(url, headers=HEADERS, stream=True, timeout=60)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"  Saved: {output_path.name}")
        return True
    except requests.RequestException as e:
        print(f"  Error downloading: {e}")
        return False


def sanitize_filename(name: str) -> str:
    """Convert a title to a safe filename."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    return name[:100]  # Limit length


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    books = get_book_pages(BOOKS_URL)

    downloaded = 0
    failed = []

    for book in books:
        print(f"\nProcessing: {book['title']}")

        pdf_url = get_pdf_url(book["url"])
        if not pdf_url:
            print(f"  No PDF found")
            failed.append(book["title"])
            continue

        # Use PDF filename from URL
        pdf_filename = pdf_url.split("/")[-1]
        output_path = OUTPUT_DIR / pdf_filename

        if download_pdf(pdf_url, output_path):
            downloaded += 1
        else:
            failed.append(book["title"])

        # Be polite to the server
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Downloaded: {downloaded} PDFs")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed books:")
        for title in failed:
            print(f"  - {title}")


if __name__ == "__main__":
    main()
