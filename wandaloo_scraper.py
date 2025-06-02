#!/usr/bin/env python3


import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import re
import argparse
from urllib.parse import urljoin, urlparse
import pandas as pd
from datetime import datetime

class WandalooPageScraper:
    def __init__(self, delay=2):
        self.base_url = "https://www.wandaloo.com"
        self.main_url_template = "https://www.wandaloo.com/neuf/maroc/0,0,0,0,0,0,-,az,{page}.html"
        self.delay = delay  # Delay between requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_soup(self, url):
        """Get BeautifulSoup object from URL with error handling"""
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def detect_max_pages(self):
        """Detect the maximum number of pages available"""
        print("🔍 Detecting maximum pages...")
        
        # Start with page 1 to look for pagination info
        soup = self.get_soup(self.main_url_template.format(page=1))
        if not soup:
            return 1
        
        # Look for pagination elements
        pagination_selectors = [
            '.pagination',
            '.pager',
            '.page-numbers',
            '[class*="pagination"]',
            '[class*="pager"]'
        ]
        
        max_page = 1
        for selector in pagination_selectors:
            pagination = soup.select(selector)
            for pag_elem in pagination:
                # Look for page numbers
                page_links = pag_elem.find_all('a', href=True)
                for link in page_links:
                    href = link.get('href', '')
                    # Extract page number from URL
                    page_match = re.search(r',(\d+)\.html', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        max_page = max(max_page, page_num)
                
                # Also check for text content that might indicate page numbers
                text_content = pag_elem.get_text()
                page_numbers = re.findall(r'\b(\d+)\b', text_content)
                for num_str in page_numbers:
                    if 1 <= int(num_str) <= 100:  # Reasonable page range
                        max_page = max(max_page, int(num_str))
        
        # If no pagination found, try to probe pages manually
        if max_page == 1:
            print("   No pagination found, probing manually...")
            for test_page in range(2, 6):  # Test  5 pages 
                test_url = self.main_url_template.format(page=test_page)
                test_soup = self.get_soup(test_url)
                if test_soup:
                    # Check if page has content
                    result_section = test_soup.find('div', id='result')
                    if result_section:
                        items_container = result_section.find('ul', class_='items')
                        if items_container and items_container.find_all('li'):
                            max_page = test_page
                        else:
                            break  # No more content
                else:
                    break  # Page doesn't exist
                time.sleep(1)  # Small delay between probes
        
        print(f"   ✓ Detected {max_page} pages")
        return max_page
    
    def extract_models_from_page(self, page_num):
        """Extract all car models and their links from a specific page"""
        print(f"\n📄 EXTRACTING MODELS FROM PAGE {page_num}")
        print("-" * 50)
        
        page_url = self.main_url_template.format(page=page_num)
        soup = self.get_soup(page_url)
        if not soup:
            return []
        
        models = []
        
        # Find the result section containing the items
        result_section = soup.find('div', id='result')
        if not result_section:
            print("❌ Could not find result section")
            return []
        
        # Find the items list within result section
        items_container = result_section.find('ul', class_='items')
        if not items_container:
            print("❌ Could not find items container in result section")
            return []
        
        # Find all car items (li elements)
        car_items = items_container.find_all('li', recursive=False)
        print(f"✓ Found {len(car_items)} car items on page {page_num}")
        
        for i, item in enumerate(car_items):
            try:
                print(f"\n📋 Processing car item {i+1}/{len(car_items)} on page {page_num}")
                
                # Extract main car name from the h3 title
                car_name = "Unknown"
                title_element = item.find('h3', class_='titre')
                if title_element:
                    title_link = title_element.find('a')
                    if title_link:
                        car_name = title_link.get_text(strip=True)
                
                print(f"   🚗 Car: {car_name}")
                
                # Find the accordion panel with individual models
                my_panel = item.find('div', class_='my-panel')
                if not my_panel:
                    print(f"   ⚠️  No my-panel found for {car_name}")
                    continue
                
                # Find all model variant items within the panel
                variant_items = my_panel.find_all('li', class_='item')
                print(f"   📊 Found {len(variant_items)} variants")
                
                for j, variant_item in enumerate(variant_items):
                    try:
                        # Extract model variant link and name
                        variant_h3 = variant_item.find('h3')
                        if not variant_h3:
                            continue
                        
                        variant_link = variant_h3.find('a')
                        if not variant_link:
                            continue
                        
                        href = variant_link.get('href')
                        if not href or 'fiche-technique' not in href:
                            continue
                        
                        full_url = urljoin(self.base_url, href)
                        model_variant = variant_link.get_text(strip=True)
                        
                        # Extract price from the variant item
                        price = ""
                        price_element = variant_item.find('li', class_='prix')
                        if price_element:
                            price = price_element.get_text(strip=True)
                        
                        models.append({
                            'page': page_num,
                            'car_name': car_name,
                            'model_variant': model_variant,
                            'url': full_url,
                            'price_preview': price
                        })
                        
                        print(f"      ✓ Variant {j+1}: {model_variant} - {price}")
                        
                    except Exception as e:
                        print(f"      ❌ Error processing variant: {e}")
                        continue
                        
            except Exception as e:
                print(f"❌ Error processing car item {i+1}: {e}")
                continue
        
        print(f"\n🎯 PAGE {page_num}: Found {len(models)} model variants across {len(car_items)} cars")
        return models
    
    def extract_model_details(self, model_info):
        """Extract detailed information from a model page"""
        model_url = model_info['url']
        print(f"\n🔍 Extracting details from: {model_url}")
        
        soup = self.get_soup(model_url)
        if not soup:
            return None
        
        details = {'url': model_url}
        
        # Extract car name (e.g., "DACIA Sandero Streetway")
        name_selectors = [
            'h1',
            '.titre-fiche h1',
            '.fiche-titre h1', 
            '.model-name h1',
            'title'
        ]
        
        for selector in name_selectors:
            name_element = soup.select_one(selector)
            if name_element:
                text = name_element.get_text(strip=True)
                # Clean up title text
                text = re.sub(r'\s*-\s*wandaloo\.com.*$', '', text)
                text = re.sub(r'\s*:\s*Tarif.*$', '', text, flags=re.IGNORECASE)
                details['name'] = text
                break
        else:
            details['name'] = "Unknown"
        
        # Extract model variant (e.g., "1.0 TCe 100 Essentiel")
        model_selectors = [
            '.titre-fiche h2',
            '.fiche-titre h2',
            'h2',
            '.model-variant',
            '.version-title'
        ]
        
        for selector in model_selectors:
            model_element = soup.select_one(selector)
            if model_element:
                text = model_element.get_text(strip=True)
                if text and text != details['name'] and len(text) > 3:
                    details['model'] = text
                    break
        else:
            # Fallback: extract from URL
            url_parts = model_url.split('/')
            if len(url_parts) > 2:
                model_part = url_parts[-2]
                details['model'] = model_part.replace('-', ' ').title()
            else:
                details['model'] = "Unknown"
        
        # Extract price (e.g., "128.000 DH")
        price_selectors = [
            '.prix',
            '.price', 
            '.tarif',
            '[class*="prix"]',
            '[class*="price"]'
        ]
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                text = price_element.get_text(strip=True)
                if 'DH' in text or any(char.isdigit() for char in text):
                    details['prix'] = text
                    break
        else:
            # Fallback: search for any text containing DH
            price_texts = soup.find_all(text=re.compile(r'\\d+[.,\\s]*\\d*.*DH', re.IGNORECASE))
            if price_texts:
                details['prix'] = price_texts[0].strip()
            else:
                details['prix'] = "Unknown"
        
        # Extract specifications from col-left
        details['specifications'] = {}
        
        # Find the col-left container
        col_left = soup.find(class_='col-left')
        if col_left:
            print("   📋 Found col-left container")
            
            # Find all accordion headers (head accordion elements)
            accordion_headers = col_left.find_all(class_=re.compile(r'head.*accordion|accordion.*head'))
            
            if not accordion_headers:
                # Try alternative selectors
                accordion_headers = col_left.find_all(['h3', 'h4', 'h5'])
                accordion_headers = [h for h in accordion_headers if 'head' in str(h.get('class', []))]
            
            print(f"   📊 Found {len(accordion_headers)} specification sections")
            
            for header in accordion_headers:
                try:
                    section_title = header.get_text(strip=True)
                    if not section_title or len(section_title) < 3:
                        continue
                    
                    print(f"      📝 Processing: {section_title}")
                    
                    # Find the content panel
                    content_panel = None
                    
                    # Try different methods to find associated content
                    candidates = [
                        header.find_next_sibling(),
                        header.parent.find_next_sibling() if header.parent else None,
                        header.find_next(class_=re.compile(r'panel|content|details'))
                    ]
                    
                    for candidate in candidates:
                        if candidate:
                            content_panel = candidate
                            break
                    
                    if content_panel:
                        # Extract all meaningful text from the panel
                        items = []
                        
                        # Look for cells (specific to Wandaloo structure)
                        cells = content_panel.find_all(class_='cell')
                        if cells:
                            for cell in cells:
                                cell_text = cell.get_text(strip=True)
                                if cell_text and len(cell_text) > 1:
                                    items.append(cell_text)
                        else:
                            # Look for other elements
                            elements = content_panel.find_all(['li', 'tr', 'td', 'div', 'span', 'p'])
                            for element in elements:
                                text = element.get_text(strip=True)
                                if text and len(text) > 2 and text not in items:
                                    # Filter out irrelevant text
                                    if not re.match(r'^[\\s\\n\\r]*$', text) and len(text) < 200:
                                        items.append(text)
                        
                        if items:
                            details['specifications'][section_title] = items[:20]  # Limit items
                            print(f"         ✓ Added {len(items)} specifications")
                        else:
                            print(f"         ⚠️  No items found")
                    else:
                        print(f"         ❌ No content panel found")
                        
                except Exception as e:
                    print(f"         ❌ Error processing section: {e}")
                    continue
        else:
            print("   ⚠️  No col-left container found")
        
        return details
    
    def scrape_pages(self, num_pages=None):
        """Scrape car models from specified number of pages"""
        print("🚀 STARTING WANDALOO CAR SCRAPER (PAGE-BASED)")
        print("="*50)
        
        start_time = datetime.now()
        
        # Determine how many pages to scrape
        if num_pages is None:
            max_pages = self.detect_max_pages()
            pages_to_scrape = max_pages
            print(f"🌍 Auto-detected {max_pages} pages - scraping ALL")
        else:
            pages_to_scrape = num_pages
            print(f"🎯 Scraping first {pages_to_scrape} pages")
        
        # Extract models from all pages
        all_models = []
        for page_num in range(1, pages_to_scrape + 1):
            models_on_page = self.extract_models_from_page(page_num)
            all_models.extend(models_on_page)
            
            if page_num < pages_to_scrape:  # Don't delay after last page
                print(f"⏳ Waiting {self.delay} seconds before next page...")
                time.sleep(self.delay)
        
        if not all_models:
            print("❌ No models found!")
            return []
        
        print(f"\\n🔄 PROCESSING {len(all_models)} MODELS FROM {pages_to_scrape} PAGES...")
        print("="*50)
        
        detailed_models = []
        
        for i, model in enumerate(all_models):
            print(f"\\n[{i+1}/{len(all_models)}] 🚗 {model['car_name']} - {model['model_variant']} (Page {model['page']})")
            print("-" * 80)
            
            details = self.extract_model_details(model)
            
            if details:
                # Merge with basic info
                final_model = {**model, **details}
                detailed_models.append(final_model)
                
                print(f"✅ SUCCESS: {details.get('name', 'Unknown')}")
                print(f"   💰 Price: {details.get('prix', 'Unknown')}")
                if details.get('specifications'):
                    print(f"   📊 Specs: {len(details['specifications'])} sections")
                    spec_names = list(details['specifications'].keys())[:3]
                    print(f"   📋 Sections: {', '.join(spec_names)}{'...' if len(details['specifications']) > 3 else ''}")
            else:
                print("❌ FAILED: Could not extract details")
            
            # Respectful delay
            if i < len(all_models) - 1:  # Don't delay after last item
                print(f"⏳ Waiting {self.delay} seconds...")
                time.sleep(self.delay)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\\n" + "="*50)
        print("🎉 SCRAPING COMPLETED!")
        print("="*50)
        print(f"📄 Pages scraped: {pages_to_scrape}")
        print(f"✅ Successfully extracted: {len(detailed_models)}/{len(all_models)} models")
        print(f"⏱️  Total time: {duration}")
        print(f"📊 Average time per model: {duration.total_seconds()/len(all_models):.1f} seconds")
        
        return detailed_models
    
    def save_to_json(self, data, filename='wandaloo_cars_pages.json'):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON data saved to {filename}")
    
    def save_to_csv(self, data, filename='wandaloo_cars_pages.csv'):
        """Save data to CSV file"""
        if not data:
            return
        
        # Flatten the data for CSV
        flattened_data = []
        for item in data:
            flat_item = {}
            for key, value in item.items():
                if key == 'specifications' and isinstance(value, dict):
                    # Flatten specifications
                    for spec_key, spec_value in value.items():
                        if isinstance(spec_value, list):
                            flat_item[f"spec_{spec_key}"] = "; ".join(spec_value)
                        else:
                            flat_item[f"spec_{spec_key}"] = str(spec_value)
                else:
                    flat_item[key] = str(value) if value else ""
            flattened_data.append(flat_item)
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"💾 CSV data saved to {filename}")
    
    def print_summary(self, data):
        """Print a summary of scraped data"""
        if not data:
            return
        
        print("\\n" + "="*50) 
        print("📈 SCRAPING SUMMARY")
        print("="*50)
        
        # Count by page
        page_counts = {}
        for item in data:
            page = item.get('page', 'Unknown')
            page_counts[page] = page_counts.get(page, 0) + 1
        
        print(f"📄 Models by page:")
        for page, count in sorted(page_counts.items()):
            print(f"   • Page {page}: {count} models")
        
        # Count by car brand
        car_counts = {}
        for item in data:
            car = item['car_name']
            car_counts[car] = car_counts.get(car, 0) + 1
        
        print(f"\\n🚗 Cars found: {len(car_counts)}")
        for car, count in sorted(car_counts.items()):
            print(f"   • {car}: {count} variants")
        
        # Specification sections found
        all_specs = set()
        for item in data:
            if 'specifications' in item:
                all_specs.update(item['specifications'].keys())
        
        print(f"\\n📊 Specification sections found: {len(all_specs)}")
        for spec in sorted(all_specs):
            print(f"   • {spec}")

def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(description='Scrape car models from Wandaloo by pages')
    parser.add_argument('--pages', type=int, help='Number of pages to scrape (default: auto-detect all)')
    parser.add_argument('--delay', type=int, default=2, help='Delay between requests in seconds')
    parser.add_argument('--output', type=str, default='wandaloo_cars_pages', help='Output filename prefix')
    
    args = parser.parse_args()
    
    scraper = WandalooPageScraper(delay=args.delay)
    
    try:
        # Scrape models
        models_data = scraper.scrape_pages(num_pages=args.pages)
        
        if models_data:
            # Save to files
            scraper.save_to_json(models_data, f'{args.output}.json')
            scraper.save_to_csv(models_data, f'{args.output}.csv')
            
            # Print summary
            scraper.print_summary(models_data)
        else:
            print("❌ No data to save!")
    
    except KeyboardInterrupt:
        print("\\n🛑 Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()