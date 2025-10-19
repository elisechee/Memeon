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

# Ensure data folders exist
os.makedirs('data', exist_ok=True)
os.makedirs('data/images', exist_ok=True)


def merge_page_into_csv(page_rows, csv_path=csv_path):
    """Simple, safe merge of a single page's rows into csv_path.
    Rules:
    - If detail_url matches an existing row, update its 'type' and 'badge' only when the new value is meaningful (not empty/'unknown'/'none').
    - If detail_url is not present, append the new row at the end (preserving chronological ordering by page runs).
    """
    expected_columns = ['name', 'year', 'origin', 'type', 'badge', 'image_filename', 'alt_description', 'detail_url']
    # read existing CSV (or create empty)
    try:
        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            existing = pd.read_csv(csv_path)
            existing.columns = existing.columns.str.strip()
        else:
            existing = pd.DataFrame(columns=expected_columns)
    except pd.errors.EmptyDataError:
        existing = pd.DataFrame(columns=expected_columns)

    # build lookup by detail_url for quick updates
    existing_lookup = { (str(r.get('detail_url') or '').strip()): r for r in existing.to_dict(orient='records') }

    appended = 0
    for row in page_rows:
        key = (row.get('detail_url') or '').strip()
        if not key:
            # append rows without detail_url
            existing = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
            appended += 1
            continue

        if key in existing_lookup:
            # update in-place in the DataFrame where detail_url matches
            mask = existing['detail_url'].fillna('').astype(str).str.strip() == key
            for field in ['type', 'badge']:
                new_val = (row.get(field) or '').strip()
                if new_val and new_val.lower() not in ('unknown', 'none'):
                    existing.loc[mask, field] = new_val
            for field in ['image_filename', 'alt_description', 'name', 'year', 'origin']:
                new_val = (row.get(field) or '').strip()
                if new_val:
                    existing.loc[mask, field] = new_val
        else:
            # append new row
            existing = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
            appended += 1

    # ensure column order
    for c in expected_columns:
        if c not in existing.columns:
            existing[c] = ''
    existing = existing[expected_columns]
    existing.to_csv(csv_path, index=False)
    return appended, len(existing)


# PART 2: Scrape Pages (edit range for more/less data)
for page_num in range(45, 46):  # Pages inclusive
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

    # collect rows for this page only
    page_rows = []

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

            page_rows.append({
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
    # merge this single page into CSV now (simple & safe)
    appended, total = merge_page_into_csv(page_rows, csv_path=csv_path)
    print(f"  Appended {appended} new rows from page {page_num}; CSV now has {total} rows")
    print("  Waiting 2 seconds before next listing page...")
    time.sleep(2)

print("All pages processed — CSV was updated after each page.")

# # Preview first 5 memes
# if len(memes) > 0:
#     print("\nFirst 5 memes scraped:")
#     for i, meme in enumerate(memes[:5], 1):
#         print(f"{i}. {meme['name']} ({meme['year']})")

