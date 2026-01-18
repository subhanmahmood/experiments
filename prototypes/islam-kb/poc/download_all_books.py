#!/usr/bin/env python3
"""
Download all books from alislam.org/books/ organized by author.
Excludes: Selected Audiobooks, eBooks on Apple/Google/Kindle, Other Languages

Structure:
- Author pages list books linking to /book/{book-name}/
- Each book page has PDF link at https://files.alislam.cloud/pdf/{name}.pdf
"""

import re
import time
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://www.alislam.org"
BOOKS_URL = "https://www.alislam.org/books/"
PDF_DIR = Path(__file__).parent / "pdfs"

# Author sections to scrape (excluding audiobooks, ebooks, other languages)
AUTHOR_SECTIONS = [
    ("hazrat-mirza-ghulam-ahmad", "Mirza-Ghulam-Ahmad"),
    ("hakeem-noor-ud-din", "Hakeem-Noor-ud-Din"),
    ("hazrat-mirza-bashiruddin-mahmud-ahmad", "Mirza-Bashir-ud-Din-Mahmud-Ahmad"),
    ("hazrat-mirza-nasir-ahmad", "Mirza-Nasir-Ahmad"),
    ("hazrat-mirza-tahir-ahmad", "Mirza-Tahir-Ahmad"),
    ("hazrat-mirza-masroor-ahmad", "Mirza-Masroor-Ahmad"),
    ("hazrat-mirza-bashir-ahmad", "Mirza-Bashir-Ahmad"),
    ("muhammad-zafrulla-khan", "Muhammad-Zafrulla-Khan"),
    ("various-authors", "Other-Authors"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def get_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_book_links_from_author_page(author_slug: str) -> list[str]:
    """Get all individual book page URLs from an author's listing page."""
    url = f"{BOOKS_URL}{author_slug}/"
    book_links = []

    try:
        soup = get_soup(url)

        # Find all links to /book/{name}/ pages
        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(BASE_URL, href)

            # Match /book/{something}/ pattern
            if re.match(r'https://www\.alislam\.org/book/[^/]+/?$', full_url):
                if full_url not in book_links:
                    book_links.append(full_url)

    except Exception as e:
        print(f"  Error fetching author page: {e}")

    return book_links


def get_pdf_url_from_book_page(book_url: str) -> str | None:
    """Get the PDF download URL from a book's detail page."""
    try:
        soup = get_soup(book_url)

        # Look for PDF link (usually at files.alislam.cloud/pdf/)
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href.lower():
                if "files.alislam.cloud" in href or "alislam.org" in href:
                    return href if href.startswith("http") else urljoin(BASE_URL, href)

        # Also check for direct PDF links in any format
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                return href if href.startswith("http") else urljoin(BASE_URL, href)

    except Exception as e:
        print(f"    Error fetching book page {book_url}: {e}")

    return None


def scrape_author_section(slug: str, author_dir_name: str) -> list[tuple[str, str]]:
    """Scrape all PDFs from an author section. Returns [(pdf_url, author_dir), ...]"""
    print(f"\nScraping: {author_dir_name}")

    # Get all book page links
    book_links = get_book_links_from_author_page(slug)
    print(f"  Found {len(book_links)} book pages")

    pdfs = []
    for i, book_url in enumerate(book_links, 1):
        pdf_url = get_pdf_url_from_book_page(book_url)
        if pdf_url:
            # Get display name from PDF filename
            filename = unquote(urlparse(pdf_url).path.split("/")[-1])
            pdfs.append((pdf_url, author_dir_name))
            print(f"  [{i}/{len(book_links)}] Found: {filename}")
        else:
            print(f"  [{i}/{len(book_links)}] No PDF on {book_url}")

        time.sleep(0.15)  # Be polite

    print(f"  Total PDFs: {len(pdfs)}")
    return pdfs


def download_pdf(pdf_url: str, author_dir: str) -> tuple[bool, str]:
    """Download a single PDF. Returns (success, message)."""
    dest_dir = PDF_DIR / author_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Get filename from URL
    filename = unquote(urlparse(pdf_url).path.split("/")[-1])
    if not filename.lower().endswith('.pdf'):
        filename = pdf_url.split("/")[-1] + ".pdf"

    filepath = dest_dir / filename

    # Skip if exists
    if filepath.exists():
        return True, f"Skipped (exists): {author_dir}/{filename}"

    try:
        response = requests.get(pdf_url, headers=HEADERS, timeout=120, stream=True)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = filepath.stat().st_size / (1024 * 1024)
        return True, f"Downloaded: {author_dir}/{filename} ({size_mb:.1f} MB)"

    except Exception as e:
        return False, f"Failed: {pdf_url} - {e}"


def main():
    print("=" * 60)
    print("Downloading all books from alislam.org/books/")
    print("=" * 60)

    # Collect all PDF URLs
    all_pdfs = []
    for slug, author_dir in AUTHOR_SECTIONS:
        pdfs = scrape_author_section(slug, author_dir)
        all_pdfs.extend(pdfs)
        time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"Total PDFs to download: {len(all_pdfs)}")
    print("=" * 60)

    if not all_pdfs:
        print("No PDFs found!")
        return

    # Download
    PDF_DIR.mkdir(exist_ok=True)
    success = skip = fail = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(download_pdf, url, author): (url, author)
            for url, author in all_pdfs
        }

        for i, future in enumerate(as_completed(futures), 1):
            ok, msg = future.result()
            if ok:
                if "Skipped" in msg:
                    skip += 1
                else:
                    success += 1
            else:
                fail += 1
            print(f"[{i}/{len(all_pdfs)}] {msg}")

    print(f"\n{'=' * 60}")
    print(f"Done! Downloaded: {success}, Skipped: {skip}, Failed: {fail}")
    print(f"Location: {PDF_DIR}")


if __name__ == "__main__":
    main()
