# =================================
# MEME SCRAPER - KNOW YOUR MEME
# =================================

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

# PART 1: Setup folders
memes = []  # List to store all meme data

# PART 2: Scrape Pages (edit range for more/less data)
for page_num in range(1, 6):  # Pages 1-5 (change range for more/less pages)
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
    meme_rows = soup.find_all('tr', class_='entry')
    print(f"  Found {len(meme_rows)} memes on this page")
    
    for row in meme_rows:
        try:
            # EXTRACT MEME NAME
            name_tag = row.find('a', class_='photo')
            if not name_tag:
                continue
            meme_name = name_tag.get('title', 'Unknown')
            
            # EXTRACT IMAGE URL
            img_tag = row.find('img')
            if not img_tag:
                continue
            image_url = img_tag.get('data-src') or img_tag.get('src')
            if not image_url:
                continue
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                image_url = 'https://knowyourmeme.com' + image_url
            
            # EXTRACT YEAR
            details_cell = row.find('td', class_='details')
            year = "Unknown"
            if details_cell:
                details_text = details_cell.get_text()
                year_match = re.search(r'(19|20)\d{2}', details_text)
                if year_match:
                    year = year_match.group(0)
            
            # CLEAN/FORMAT image filename
            safe_name = "".join(
                c for c in meme_name if c.isalnum() or c in (' ', '-', '_')
            ).strip()[:50]
            image_filename = f"{safe_name}.jpg"
            image_path = f"data/images/{image_filename}"
            
            # DOWNLOAD IMAGE (skip if exists)
            if not os.path.exists(image_path):
                try:
                    img_response = requests.get(image_url, timeout=10)
                    if img_response.status_code == 200:
                        with open(image_path, 'wb') as f:
                            f.write(img_response.content)
                        print(f"    Downloaded: {meme_name}")
                    else:
                        print(f"    WARNING: Could not download image for: {meme_name}")
                        continue
                except Exception as e:
                    print(f"    Error downloading {meme_name}: {e}")
                    continue
            else:
                print(f"    Already have: {meme_name}")
            
            # SAVE meme data (name, year, image filename, source, category)
            memes.append({
                'name': meme_name,
                'year': year,
                'image_filename': image_filename,
                'source': 'Know Your Meme',
                'category': 'Unknown'  # Optional (add later if desired)
            })
        except Exception as e:
            print(f"    Error processing a meme: {e}")
            continue
    print(f"  Waiting 2 seconds before next page...")
    time.sleep(2)

# PART 3: Save to CSV
print("\nSaving data to CSV...")
df = pd.DataFrame(memes)
df.to_csv('data/memes.csv', index=False)

# PART 4: Summary
print("\n==============================")
print("✨ SCRAPING COMPLETE! ✨")
print("==============================")
print(f"Total memes scraped: {len(memes)}")
print(f"Data saved to: data/memes.csv")
print(f"Images saved to: data/images/")
print("==============================")

# Preview first 5 memes
if len(memes) > 0:
    print("\nFirst 5 memes scraped:")
    for i, meme in enumerate(memes[:5], 1):
        print(f"{i}. {meme['name']} ({meme['year']})")
