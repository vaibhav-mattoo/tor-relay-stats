#!/usr/bin/env python3
"""
Script to download and parse Tor bandwidth files from CollecTor
for March 1, 2024 to April 1, 2024
"""

import urllib.request
import tarfile
import lzma
import os
import re
from datetime import datetime
from collections import defaultdict
from urllib.error import HTTPError


def download_bandwidth_file(month_year, output_dir="bandwidth_data"):
    """Download bandwidth file for a specific month"""
    url = f"https://collector.torproject.org/archive/relay-descriptors/bandwidths/bandwidths-{month_year}.tar.xz"
    filename = f"bandwidths-{month_year}.tar.xz"
    filepath = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(filepath):
        print(f"{filename} already exists. Skipping download.")
        return filepath

    print(f"Downloading {filename}...")
    try:
        urllib.request.urlretrieve(url, filepath)
        print(f"Downloaded {filename}")
        return filepath
    except HTTPError as e:
        if e.code == 404:
            print(f"ERROR: {filename} not found (HTTP 404).")
            print(f"The file may not be published yet or the URL is incorrect.")
            print(f"Attempted URL: {url}")
            return None
        else:
            raise


def extract_bandwidth_file(filepath, output_dir="bandwidth_data"):
    """Extract the tar.xz file"""
    if filepath is None:
        return None

    extract_dir = filepath.replace(".tar.xz", "")

    if os.path.exists(extract_dir):
        print(f"Already extracted to {extract_dir}")
        return extract_dir

    print(f"Extracting {filepath}...")
    with tarfile.open(filepath, "r:xz") as tar:
        tar.extractall(path=output_dir)
    print(f"Extracted to {output_dir}")
    return extract_dir


if __name__ == "__main__":
    # Download both months
    print("Downloading bandwidth files...")
    print()

    mar_file = download_bandwidth_file("2024-03")
    apr_file = download_bandwidth_file("2024-04")

    print("\nExtracting files...")

    if mar_file:
        mar_dir = extract_bandwidth_file(mar_file)
        print(f"March 2024 data extracted successfully")
    else:
        print("Skipping March 2024 extraction (download failed)")

    if apr_file:
        apr_dir = extract_bandwidth_file(apr_file)
        print(f"April 2024 data extracted successfully")
    else:
        print("Skipping April 2024 extraction (download failed)")

    print("\nNote: The extraction creates a directory with individual bandwidth files.")
    print("Each file represents bandwidth measurements at a specific time.")
    print("\nNext, use the analysis script to process these files.")
