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

# PART 1: Setup folders
memes = []  # List to store all meme data

# PART 2: Scrape Pages (edit range for more/less data)
for page_num in range(3, 51):  # Pages 1-5 (change range for more/less pages)
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
            try:
                det_resp = requests.get(meme_link, timeout=10)
                det_soup = BeautifulSoup(det_resp.content, 'html.parser')

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
old_df = pd.read_csv('data/memes.csv')
new_df = pd.DataFrame(memes)
combined_df = pd.concat([old_df, new_df], ignore_index=True)

# Remove duplicates by unique meme property (like 'detail_url' or 'name'):
combined_df = combined_df.drop_duplicates(subset=['detail_url'])

combined_df.to_csv('data/memes.csv', index=False)

print("Done! See data/memes.csv and your images folder.")

# # Preview first 5 memes
# if len(memes) > 0:
#     print("\nFirst 5 memes scraped:")
#     for i, meme in enumerate(memes[:5], 1):
#         print(f"{i}. {meme['name']} ({meme['year']})")

