# =================================
# MEME SCRAPER - KNOW YOUR MEME
# =================================

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

base_url = "https://knowyourmeme.com"
csv_path = 'data/memes.csv'

# PART 1: Setup folders
memes = []  # List to store all meme data

# PART 2: Scrape Pages (edit range for more/less data)
for page_num in range(2, 3):  # Pages 1-5 (change range for more/less pages)
    print(f"\nScraping page {page_num}...")
    url = f"https://knowyourmeme.com/categories/meme/page/{page_num}?sort=chronological&status=confirmed"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Error: Got status code {response.status_code}")
            continue
    
    except Exception as e:
        print(f"Error downloading page: {e}")
        continue
    
    soup = BeautifulSoup(response.content, 'html.parser')
    meme_cards = soup.find_all('a', class_='item')

    # for tag in soup.find_all('a'):
    #     classes = tag.get('class', [])
    #     # Print any <a> with class attribute, especially 'item'
    #     if any('item' in c for c in classes):
    #         print("  DEBUG <a>:", classes, tag.get('href'))

    print(f"  Found {len(meme_cards)} memes on this page")
    
    for card in meme_cards:
        # print("Debug: Found meme card!", card.get('href'))
        try:
            name_elem = card.find('h3')
            meme_name = name_elem.get_text(strip=True) if name_elem else 'Unknown'

            # Image extraction: use first inner <img> with data-image
            img_elem = card.find('img', attrs={'data-image': True})
            image_url = img_elem['data-image'] if img_elem else None
            alt_text = img_elem.get('alt', 'Unknown') if img_elem else ''

            # Detail page URL
            meme_link = card['href']
            if not meme_link.startswith('http'):
                meme_link = base_url + meme_link

            # Now, go to the detail page for year/origin
            print(f"  Scraping detail page: {meme_link}")
            year = "Unknown"
            origin = "Unknown"
            type = "Unknown"
            badge = "None"
            try:
                det_resp = requests.get(meme_link, timeout=10)
                det_soup = BeautifulSoup(det_resp.content, 'html.parser')
                for dt in det_soup.select('dt'):
                    if dt.get_text(strip=True).lower() == 'type:':
                        type_dd = dt.find_next_sibling('dd')
                        if type_dd:
                            # print("    DEBUG Type found:", type_dd.get_text(strip=True))
                            type = type_dd.get_text(strip=True)
                        break
                # print what is found at dt.get_text(strip=True).lower() == 'type:'
                
                for dt in det_soup.select('dt'):
                    if dt.get_text(strip=True).lower() == 'badges:':
                        badge_dd = dt.find_next_sibling('dd')
                        if badge_dd:
                            badge = badge_dd.get_text(strip=True)
                        break
                # Find Year: look for <dt>Year</dt> then following <dd>
                for dt in det_soup.select('dt'):
                    if dt.get_text(strip=True) == 'Year':
                        year_dd = dt.find_next_sibling('dd')
                        if year_dd:
                            year = year_dd.get_text(strip=True)
                        break
                # Find Origin
                for dt in det_soup.select('dt'):
                    if dt.get_text(strip=True) == 'Origin':
                        origin_dd = dt.find_next_sibling('dd')
                        if origin_dd:
                            origin = origin_dd.get_text(strip=True)
                        break
                time.sleep(1)  # Polite pause
            except Exception as e:
                print(f"    Error scraping details: {e}")
                # year and origin remain 'Unknown'

            # Save image (skip if exists)
            safe_name = "".join(c for c in meme_name if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
            image_filename = f"{safe_name}.jpg"
            image_path = f"data/images/{image_filename}"
            if image_url and not os.path.exists(image_path):
                try:
                    img_resp = requests.get(image_url, timeout=10)
                    if img_resp.status_code == 200:
                        with open(image_path, 'wb') as f:
                            f.write(img_resp.content)
                        print(f"    Downloaded image: {meme_name}")
                except Exception as e:
                    print(f"    Could not download image: {e}")
            elif os.path.exists(image_path):
                print(f"    Already have image: {meme_name}")

            memes.append({
                'name': meme_name,
                'year': year,
                'origin': origin,
                'type': type,
                'badge': badge,
                'image_filename': image_filename,
                'alt_description': alt_text,
                'detail_url': meme_link
            })
        except Exception as e:
            print(f"    Error processing meme card: {e}")
            continue
    print("  Waiting 2 seconds before next listing page...")
    time.sleep(2)

# Save as CSV
# Ensure data directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('data/images', exist_ok=True)

# Try to read existing CSV, handle missing or empty file gracefully
expected_columns = ['name', 'year', 'origin', 'type', 'badge', 'image_filename', 'alt_description', 'detail_url']
try:
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        old_df = pd.read_csv(csv_path)
        # normalize column names
        old_df.columns = old_df.columns.str.strip()
    else:
        # empty or missing file -> create empty DataFrame with expected columns
        old_df = pd.DataFrame(columns=expected_columns)
except pd.errors.EmptyDataError:
    print("Warning: data/memes.csv exists but is empty or malformed. Creating a fresh DataFrame.")
    old_df = pd.DataFrame(columns=expected_columns)

new_df = pd.DataFrame(memes)

# Ensure new_df has the same columns order (add missing expected columns)
for c in expected_columns:
    if c not in new_df.columns:
        new_df[c] = ''

# Normalize column names
old_df.columns = old_df.columns.str.strip()
new_df.columns = new_df.columns.str.strip()

# Build a lookup for new rows by detail_url (preserve first occurrence per URL)
new_lookup = {}
for _, row in new_df.iterrows():
    key = (row.get('detail_url') or '').strip()
    if not key:
        continue
    if key not in new_lookup:
        new_lookup[key] = row.to_dict()

# Build set of existing detail_url values safely
if 'detail_url' in old_df.columns:
    existing_urls = set(old_df['detail_url'].fillna('').astype(str).str.strip())
    existing_urls.discard('')
else:
    existing_urls = set()

# Output rows: start with old rows in their existing order, merging in new values where meaningful
output_rows = []
for old_row in old_df.to_dict(orient='records'):
    detail = (old_row.get('detail_url') or '').strip()
    if not detail:
        output_rows.append(old_row)
        continue

    if detail in new_lookup:
        new_row = new_lookup[detail]
        merged = dict(old_row)  # copy
        # update selective fields only when new value is meaningful
        for field in ['type', 'badge']:
            new_val = (new_row.get(field) or '').strip()
            old_val = (merged.get(field) or '').strip()
            if new_val and new_val.lower() not in ('unknown', 'none'):
                merged[field] = new_val
        # update other meta fields if present in new row
        for field in ['image_filename', 'alt_description', 'name', 'year', 'origin']:
            new_val = (new_row.get(field) or '').strip()
            if new_val:
                merged[field] = new_val
        output_rows.append(merged)
    else:
        output_rows.append(old_row)

# Append truly new rows in the order they were scraped
for _, new_row in new_df.iterrows():
    detail = (new_row.get('detail_url') or '').strip()
    if not detail:
        # append rows without detail_url as they appear
        output_rows.append({c: (new_row.get(c) or '') for c in expected_columns})
        continue
    if detail in existing_urls:
        continue
    output_rows.append({c: (new_row.get(c) or '') for c in expected_columns})

# Write final CSV preserving chronological order (old rows remain in order; new rows appended)
final_df = pd.DataFrame(output_rows, columns=expected_columns)
final_df.to_csv(csv_path, index=False)

print(f"Done! Wrote {len(final_df)} rows to {csv_path}. See data/images/ for images.")

# # Preview first 5 memes
# if len(memes) > 0:
#     print("\nFirst 5 memes scraped:")
#     for i, meme in enumerate(memes[:5], 1):
#         print(f"{i}. {meme['name']} ({meme['year']})")

