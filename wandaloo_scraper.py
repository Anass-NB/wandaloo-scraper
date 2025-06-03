#!/usr/bin/env python3
"""
Enhanced Wandaloo Car Scraper with Image Support and Organized Specifications

"""

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

class EnhancedWandalooScraper:
    def __init__(self, delay=2):
        self.base_url = "https://www.wandaloo.com"
        self.main_url_template = "https://www.wandaloo.com/neuf/maroc/0,0,0,0,0,0,-,az,{page}.html"
        self.delay = delay
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
        
        soup = self.get_soup(self.main_url_template.format(page=1))
        if not soup:
            return 1
        
        max_page = 1
        
        # Look for pagination elements
        pagination_selectors = ['.pagination', '.pager', '.page-numbers', '[class*="pagination"]', '[class*="pager"]']
        
        for selector in pagination_selectors:
            pagination = soup.select(selector)
            for pag_elem in pagination:
                page_links = pag_elem.find_all('a', href=True)
                for link in page_links:
                    href = link.get('href', '')
                    page_match = re.search(r',(\d+)\.html', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        max_page = max(max_page, page_num)
        
        # If no pagination found, probe manually
        if max_page == 1:
            print("   No pagination found, probing manually...")
            for test_page in range(2, 6):
                test_url = self.main_url_template.format(page=test_page)
                test_soup = self.get_soup(test_url)
                if test_soup:
                    result_section = test_soup.find('div', id='result')
                    if result_section:
                        items_container = result_section.find('ul', class_='items')
                        if items_container and items_container.find_all('li'):
                            max_page = test_page
                        else:
                            break
                else:
                    break
                time.sleep(1)
        
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
        
        result_section = soup.find('div', id='result')
        if not result_section:
            print("❌ Could not find result section")
            return []
        
        items_container = result_section.find('ul', class_='items')
        if not items_container:
            print("❌ Could not find items container in result section")
            return []
        
        car_items = items_container.find_all('li', recursive=False)
        print(f"✓ Found {len(car_items)} car items on page {page_num}")
        
        for i, item in enumerate(car_items):
            try:
                print(f"\n📋 Processing car item {i+1}/{len(car_items)} on page {page_num}")
                
                # Extract main car name
                car_name = "Unknown"
                title_element = item.find('h3', class_='titre')
                if title_element:
                    title_link = title_element.find('a')
                    if title_link:
                        car_name = title_link.get_text(strip=True)
                
                print(f"   🚗 Car: {car_name}")
                
                # Extract main car image
                main_image_url = "#"
                img_container = item.find('div', class_='col-sm-3')
                if img_container:
                    img_element = img_container.find('img')
                    if img_element and img_element.get('src'):
                        main_image_url = urljoin(self.base_url, img_element.get('src'))
                
                # Find model variants
                my_panel = item.find('div', class_='my-panel')
                if not my_panel:
                    print(f"   ⚠️  No my-panel found for {car_name}")
                    continue
                
                variant_items = my_panel.find_all('li', class_='item')
                print(f"   📊 Found {len(variant_items)} variants")
                
                for j, variant_item in enumerate(variant_items):
                    try:
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
                        
                        # Extract price
                        price = "#"
                        price_element = variant_item.find('li', class_='prix')
                        if price_element:
                            price = price_element.get_text(strip=True)
                        
                        models.append({
                            'page': page_num,
                            'car_name': car_name,
                            'model_variant': model_variant,
                            'url': full_url,
                            'price_preview': price,
                            'main_image_url': main_image_url
                        })
                        
                        print(f"      ✓ Variant {j+1}: {model_variant} - {price}")
                        
                    except Exception as e:
                        print(f"      ❌ Error processing variant: {e}")
                        continue
                        
            except Exception as e:
                print(f"❌ Error processing car item {i+1}: {e}")
                continue
        
        print(f"\n🎯 PAGE {page_num}: Found {len(models)} model variants")
        return models
    
    def detect_image_value(self, img_element):
        """Detect if an image represents OUI/YES or NO based on its attributes"""
        if not img_element:
            return "#"
        
        # Check src, alt, title attributes for clues
        src = img_element.get('src', '').lower()
        alt = img_element.get('alt', '').lower()
        title = img_element.get('title', '').lower()
        
        # Common indicators for YES/OUI
        yes_indicators = ['oui', 'yes', 'check', 'tick', 'ok', 'valid', 'green', 'success']
        # Common indicators for NO
        no_indicators = ['no', 'non', 'cross', 'x', 'invalid', 'red', 'fail', 'error']
        
        all_text = f"{src} {alt} {title}".lower()
        
        # Check for YES indicators
        for indicator in yes_indicators:
            if indicator in all_text:
                return "OUI"
        
        # Check for NO indicators  
        for indicator in no_indicators:
            if indicator in all_text:
                return "NO"
        
        # If unclear, try to determine from filename patterns
        if 'oui' in src or 'yes' in src or 'check' in src:
            return "OUI"
        elif 'no' in src or 'non' in src or 'cross' in src:
            return "NO"
        
        return "#"
    
    def parse_specification_cell(self, cell):
        """Parse a specification cell to extract key-value pairs"""
        if not cell:
            return {}
        
        cell_text = cell.get_text(strip=True)
        if not cell_text:
            return {}
        
        result = {}
        
        # Look for images in the cell (for OUI/NO values)
        img_elements = cell.find_all('img')
        
        # If cell contains an image, try to detect its value
        if img_elements:
            for img in img_elements:
                img_value = self.detect_image_value(img)
                if img_value != "#":
                    # Try to find the associated label
                    # Remove image from text and use remaining as key
                    text_without_img = cell_text
                    result[text_without_img or "value"] = img_value
                    return result
        
        # Parse text-based specifications
        # Look for common patterns like "Key: Value" or "KeyValue"
        
        # Pattern 1: "Key: Value"
        if ':' in cell_text:
            parts = cell_text.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                result[key] = value if value else "#"
                return result
        
        # Pattern 2: Look for known specification patterns
        spec_patterns = [
            (r'Motorisation\s*(.+)', 'Motorisation'),
            (r'Energie\s*(.+)', 'Energie'),
            (r'Puissance\s*fiscale\s*(.+)', 'Puissance_fiscale'),
            (r'Transmission\s*(.+)', 'Transmission'),
            (r'Architecture\s*(.+)', 'Architecture'),
            (r'Cylindrée\s*(.+)', 'Cylindree'),
            (r'Couple\s*maxi\s*\.?\s*(.+)', 'Couple_maxi'),
            (r'Conso\.\s*ville\s*(.+)', 'Conso_ville'),
            (r'Conso\.\s*route\s*(.+)', 'Conso_route'),
            (r'Conso\.\s*mixte\s*(.+)', 'Conso_mixte'),
            (r'Emission\s*CO2\s*(.+)', 'Emission_CO2'),
            (r'Vitesse\s*maxi\s*\.?\s*(.+)', 'Vitesse_maxi'),
            (r'Accélération\s*0-100\s*km/h\s*(.+)', 'Acceleration_0_100'),
            (r'Catégorie\s*(.+)', 'Categorie'),
            (r'Carrosserie\s*(.+)', 'Carrosserie'),
            (r'Nombre\s*de\s*places\s*(.+)', 'Nombre_places'),
            (r'Poids\s*à\s*vide\s*(.+)', 'Poids_vide'),
            (r'Longueur\s*(.+)', 'Longueur'),
            (r'Largeur\s*(.+)', 'Largeur'),
            (r'Hauteur\s*(.+)', 'Hauteur'),
            (r'Empattement\s*(.+)', 'Empattement'),
            (r'Airbags\s*(.+)', 'Airbags'),
            (r'ABS\s*(.+)', 'ABS'),
            (r'ESP\s*(.+)', 'ESP'),
            (r'Climatisation\s*(.+)', 'Climatisation'),
            (r'Système\s*audio\s*(.+)', 'Systeme_audio'),
            (r'Jantes\s*(.+)', 'Jantes'),
            (r'Sellerie\s*(.+)', 'Sellerie'),
            (r'Phares\s*(.+)', 'Phares'),
            (r'Toit\s*(.+)', 'Toit')
        ]
        
        for pattern, key in spec_patterns:
            match = re.search(pattern, cell_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                result[key] = value if value else "#"
                return result
        
        # If no specific pattern matches, try to split on common delimiters
        if len(cell_text) > 0:
            # Look for standalone values that might be keys
            if cell_text in ['ABS', 'ESP', 'Airbags', 'Climatisation', 'Start & Stop']:
                result[cell_text] = "#"  # Will be filled if there's an associated value
                return result
        
        # If nothing else works, return the text as a generic value
        return {"value": cell_text}
    
    def extract_model_details(self, model_info):
        """Extract detailed information from a model page including images and organized specs"""
        model_url = model_info['url']
        print(f"\n🔍 Extracting details from: {model_url}")
        
        soup = self.get_soup(model_url)
        if not soup:
            return None
        
        details = {'url': model_url}
        
        # Extract car name
        name_selectors = ['h1', '.titre-fiche h1', '.fiche-titre h1', '.model-name h1', 'title']
        
        for selector in name_selectors:
            name_element = soup.select_one(selector)
            if name_element:
                text = name_element.get_text(strip=True)
                text = re.sub(r'\s*-\s*wandaloo\.com.*$', '', text)
                text = re.sub(r'\s*:\s*Tarif.*$', '', text, flags=re.IGNORECASE)
                details['name'] = text
                break
        else:
            details['name'] = "#"
        
        # Extract model variant
        model_selectors = ['.titre-fiche h2', '.fiche-titre h2', 'h2', '.model-variant', '.version-title']
        
        for selector in model_selectors:
            model_element = soup.select_one(selector)
            if model_element:
                text = model_element.get_text(strip=True)
                if text and text != details['name'] and len(text) > 3:
                    details['model'] = text
                    break
        else:
            url_parts = model_url.split('/')
            if len(url_parts) > 2:
                model_part = url_parts[-2]
                details['model'] = model_part.replace('-', ' ').title()
            else:
                details['model'] = "#"
        
        # Extract price
        price_selectors = ['.prix', '.price', '.tarif', '[class*="prix"]', '[class*="price"]']
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                text = price_element.get_text(strip=True)
                if 'DH' in text or any(char.isdigit() for char in text):
                    details['prix'] = text
                    break
        else:
            price_texts = soup.find_all(text=re.compile(r'\d+[.,\s]*\d*.*DH', re.IGNORECASE))
            if price_texts:
                details['prix'] = price_texts[0].strip()
            else:
                details['prix'] = "#"
        
        # Extract main car image from the page
        details['images'] = []
        
        # Look for main car images
        image_selectors = [
            '.col-sm-5 img',  # Main image area
            '.car-image img',
            '.model-image img',
            '.fiche img[src*="Voiture-Neuve"]',
            'img[alt*="' + details.get('name', '').split()[0] + '"]' if details.get('name') != "#" else 'img'
        ]
        
        for selector in image_selectors:
            try:
                images = soup.select(selector)
                for img in images:
                    src = img.get('src')
                    if src and ('Voiture-Neuve' in src or 'voiture' in src.lower()):
                        full_img_url = urljoin(self.base_url, src)
                        if full_img_url not in details['images']:
                            details['images'].append(full_img_url)
            except:
                continue
        
        # If no specific car images found, get the main image from model_info
        if not details['images'] and model_info.get('main_image_url') != "#":
            details['images'].append(model_info['main_image_url'])
        
        # Extract organized specifications from col-left
        details['specifications'] = {}
        
        col_left = soup.find(class_='col-left')
        if col_left:
            print("   📋 Found col-left container")
            
            accordion_headers = col_left.find_all(class_=re.compile(r'head.*accordion|accordion.*head'))
            
            if not accordion_headers:
                accordion_headers = col_left.find_all(['h3', 'h4', 'h5'])
                accordion_headers = [h for h in accordion_headers if 'head' in str(h.get('class', []))]
            
            print(f"   📊 Found {len(accordion_headers)} specification sections")
            
            for header in accordion_headers:
                try:
                    section_title = header.get_text(strip=True)
                    if not section_title or len(section_title) < 3:
                        continue
                    
                    # Clean section title
                    section_title = re.sub(r'Afficher[+-]', '', section_title).strip()
                    
                    print(f"      📝 Processing: {section_title}")
                    
                    # Find content panel
                    content_panel = None
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
                        section_specs = {}
                        
                        # Look for cells (Wandaloo structure)
                        cells = content_panel.find_all(class_='cell')
                        if cells:
                            for cell in cells:
                                cell_specs = self.parse_specification_cell(cell)
                                section_specs.update(cell_specs)
                        else:
                            # Look for other elements
                            elements = content_panel.find_all(['li', 'tr', 'td', 'div', 'span'])
                            for element in elements:
                                cell_specs = self.parse_specification_cell(element)
                                section_specs.update(cell_specs)
                        
                        # Ensure all values have defaults
                        for key, value in section_specs.items():
                            if not value or value.strip() == "":
                                section_specs[key] = "#"
                        
                        if section_specs:
                            details['specifications'][section_title] = section_specs
                            print(f"         ✓ Added {len(section_specs)} specifications")
                        else:
                            print(f"         ⚠️  No structured specs found")
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
        print("🚀 STARTING ENHANCED WANDALOO CAR SCRAPER")
        print("="*50)
        
        start_time = datetime.now()
        
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
            
            if page_num < pages_to_scrape:
                print(f"⏳ Waiting {self.delay} seconds before next page...")
                time.sleep(self.delay)
        
        if not all_models:
            print("❌ No models found!")
            return []
        
        print(f"\n🔄 PROCESSING {len(all_models)} MODELS FROM {pages_to_scrape} PAGES...")
        print("="*50)
        
        detailed_models = []
        
        for i, model in enumerate(all_models):
            print(f"\n[{i+1}/{len(all_models)}] 🚗 {model['car_name']} - {model['model_variant']} (Page {model['page']})")
            print("-" * 80)
            
            details = self.extract_model_details(model)
            
            if details:
                final_model = {**model, **details}
                detailed_models.append(final_model)
                
                print(f"✅ SUCCESS: {details.get('name', '#')}")
                print(f"   💰 Price: {details.get('prix', '#')}")
                print(f"   🖼️  Images: {len(details.get('images', []))} found")
                if details.get('specifications'):
                    print(f"   📊 Specs: {len(details['specifications'])} sections")
                    for section_name, section_specs in details['specifications'].items():
                        print(f"      • {section_name}: {len(section_specs)} items")
            else:
                print("❌ FAILED: Could not extract details")
            
            if i < len(all_models) - 1:
                print(f"⏳ Waiting {self.delay} seconds...")
                time.sleep(self.delay)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "="*50)
        print("🎉 SCRAPING COMPLETED!")
        print("="*50)
        print(f"📄 Pages scraped: {pages_to_scrape}")
        print(f"✅ Successfully extracted: {len(detailed_models)}/{len(all_models)} models")
        print(f"⏱️  Total time: {duration}")
        
        return detailed_models
    
    def save_to_json(self, data, filename='enhanced_wandaloo_cars.json'):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON data saved to {filename}")
    
    def save_to_csv(self, data, filename='enhanced_wandaloo_cars.csv'):
        """Save data to CSV file with flattened specifications"""
        if not data:
            return
        
        flattened_data = []
        for item in data:
            flat_item = {}
            for key, value in item.items():
                if key == 'specifications' and isinstance(value, dict):
                    # Flatten specifications with section prefixes
                    for section_name, section_specs in value.items():
                        if isinstance(section_specs, dict):
                            for spec_key, spec_value in section_specs.items():
                                flat_key = f"{section_name}_{spec_key}".replace(' ', '_').replace('&', 'and')
                                flat_item[flat_key] = str(spec_value) if spec_value else "#"
                        else:
                            flat_key = f"{section_name}_value".replace(' ', '_').replace('&', 'and')
                            flat_item[flat_key] = str(section_specs) if section_specs else "#"
                elif key == 'images' and isinstance(value, list):
                    # Join image URLs
                    flat_item['images'] = "; ".join(value) if value else "#"
                else:
                    flat_item[key] = str(value) if value else "#"
            flattened_data.append(flat_item)
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"💾 CSV data saved to {filename}")
    
    def print_summary(self, data):
        """Print a summary of scraped data"""
        if not data:
            return
        
        print("\n" + "="*50) 
        print("📈 ENHANCED SCRAPING SUMMARY")
        print("="*50)
        
        # Count by page
        page_counts = {}
        for item in data:
            page = item.get('page', 'Unknown')
            page_counts[page] = page_counts.get(page, 0) + 1
        
        print(f"📄 Models by page:")
        for page, count in sorted(page_counts.items()):
            print(f"   • Page {page}: {count} models")
        
        # Images summary
        total_images = sum(len(item.get('images', [])) for item in data)
        models_with_images = len([item for item in data if item.get('images')])
        
        print(f"\n🖼️  Images:")
        print(f"   • Total images found: {total_images}")
        print(f"   • Models with images: {models_with_images}/{len(data)}")
        
        # Specifications summary
        all_sections = set()
        all_spec_keys = set()
        for item in data:
            if 'specifications' in item:
                all_sections.update(item['specifications'].keys())
                for section_specs in item['specifications'].values():
                    if isinstance(section_specs, dict):
                        all_spec_keys.update(section_specs.keys())
        
        print(f"\n📊 Specifications:")
        print(f"   • Sections found: {len(all_sections)}")
        print(f"   • Unique spec keys: {len(all_spec_keys)}")
        print(f"   • Sample sections: {', '.join(list(all_sections)[:3])}...")

def main():
    """Main function to run the enhanced scraper"""
    parser = argparse.ArgumentParser(description='Enhanced Wandaloo Car Scraper with Images and Organized Specs')
    parser.add_argument('--pages', type=int, help='Number of pages to scrape (default: auto-detect all)')
    parser.add_argument('--delay', type=int, default=2, help='Delay between requests in seconds')
    parser.add_argument('--output', type=str, default='enhanced_wandaloo_cars', help='Output filename prefix')
    
    args = parser.parse_args()
    
    scraper = EnhancedWandalooScraper(delay=args.delay)
    
    try:
        models_data = scraper.scrape_pages(num_pages=args.pages)
        
        if models_data:
            scraper.save_to_json(models_data, f'{args.output}.json')
            scraper.save_to_csv(models_data, f'{args.output}.csv')
            scraper.print_summary(models_data)
        else:
            print("❌ No data to save!")
    
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()