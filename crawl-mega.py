import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
import re

class MegazipCrawler:
    def __init__(self):
        self.base_url = "https://www.megazip.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        self.delay = 1
        
    def get_page(self, url):
        """Get page with error handling"""
        try:
            print(f"Fetching: {url}")
            time.sleep(self.delay)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def get_models(self):
        """Get all models"""
        url = f"{self.base_url}/zapchasti-dlya-avtomobilej/toyota#sales-region=all"
        print("\n" + "="*80)
        print("CRAWLING MODELS")
        print("="*80)
        
        soup = self.get_page(url)
        if not soup:
            return []
        
        models = []
        model_links = soup.find_all('a', class_='s-catalog__model-link')
        
        total_models = len(model_links)
        for idx, link in enumerate(model_links, 1):
            model_info = {
                'name': link.text.strip(),
                'url': urljoin(self.base_url, link.get('href')),
                'data_id': link.parent.get('data-id'),
                'frames': []
            }
            models.append(model_info)
            print(f"[{idx}/{total_models}] {model_info['name']} (ID: {model_info['data_id']})")  
        
        print(f"\n  Total: {len(models)} models")
        return models
    
    def get_model_frames(self, model):
        """Get frames for a model"""
        print(f"\n{'─'*80}")
        print(f"FRAMES FOR {model['name']}")
        print(f"{'─'*80}")
        
        soup = self.get_page(model['url'])
        if not soup:
            return []
        
        frames = []
        frame_container = soup.find('div', class_='s-catalog__model-group')
        if frame_container:
            frame_links = frame_container.find_all('a', class_='s-catalog__model-link')
            
            total_frames = len(frame_links)  
            for idx, link in enumerate(frame_links, 1): 
                frame_info = {
                    'name': link.text.strip(),
                    'url': urljoin(self.base_url, link.get('href')) + '#year=all&engine-1=all&atm-mtm=all',
                    'data_id': link.parent.get('data-id'),
                    'variants': []
                }
                frames.append(frame_info)
                print(f"[{idx}/{total_frames}] {frame_info['name']} (ID: {frame_info['data_id']})")
        
        print(f"  Total: {len(frames)} frames")
        return frames
    
    def get_frame_variants(self, frame, model_name):
        """Get variants for a frame"""
        print(f"\n  {'┄'*70}")
        print(f"VARIANTS FOR {model_name} - {frame['name']}")
        print(f"  {'┄'*70}")
        
        soup = self.get_page(frame['url'])
        if not soup:
            return []
        
        variants = []
        variant_items = soup.find_all('li', class_='s-catalog__body-variants-item')
        
        total_variants = len(variant_items)  
        for idx, item in enumerate(variant_items, 1):  
            variant_data = self.parse_variant_item(item)
            if variant_data:
                variants.append(variant_data)
                print(f"[{idx}/{total_variants}] {variant_data['code']} | {variant_data['year']}") 
        
        print(f"    Total: {len(variants)} variants")
        return variants
    
    def parse_variant_item(self, item):
        """Parse variant details"""
        try:
            data_id = item.get('data-id')
            link_elem = item.find('a', class_='s-catalog__body-variants-name')
            if not link_elem:
                return None
            
            url = urljoin(self.base_url, link_elem.get('href'))
            code = link_elem.find('span', class_='search_value').text.strip()
            
            attrs = {}
            attr_dls = item.find_all('dl', class_='s-catalog__attrs')
            
            for dl in attr_dls:
                terms = dl.find_all('dt', class_='s-catalog__attrs-term')
                datas = dl.find_all('dd', class_='s-catalog__attrs-data')
                
                for term, data in zip(terms, datas):
                    key = term.text.strip().lower().replace(' ', '_')
                    value = data.text.strip()
                    attrs[key] = value
            
            return {
                'data_id': data_id,
                'code': code,
                'url': url,
                'year': attrs.get('year', ''),
                'engine': attrs.get('engine', ''),
                'transmission': attrs.get('transmission', ''),
                'grade': attrs.get('grade', ''),
                'all_attributes': attrs,
                'part_groups': []
            }
        except Exception as e:
            print(f"    ✗ Error parsing variant: {str(e)}")
            return None
    
    def get_variant_part_groups(self, variant, model_name, frame_name, variant_index=None, total_variants=None):
        """Get part groups for a variant"""
        print(f"\n    {'·'*60}")
        if variant_index and total_variants:
            print(f" PART GROUPS FOR {variant['code']} [{variant_index}/{total_variants}]")
        else:
            print(f" PART GROUPS FOR {variant['code']}")
        print(f"    {'·'*60}")
        
        soup = self.get_page(variant['url'])
        if not soup:
            return []
        
        part_groups = []
        group_items = soup.find_all('li', class_='part-group__item')
        
        total_groups = len(group_items) 
        for idx, item in enumerate(group_items, 1):
            group_data = self.parse_part_group_item(item)
            if group_data:
                part_groups.append(group_data)
                print(f"[{idx}/{total_groups}] {group_data['name']} (ID: {group_data['id']})") 
        
        print(f"      Total: {len(part_groups)} part groups")
        return part_groups
    
    def parse_part_group_item(self, item):
        """Parse part group details"""
        try:
            group_id = item.get('id', '').replace('part-group-', '')
            
            link = item.find('a', class_='part-group__name')
            if not link:
                return None
            
            name = link.text.strip()
            url = urljoin(self.base_url, link.get('href'))
            
            description_elem = item.find('p', class_='part-group__description')
            description = description_elem.text.strip() if description_elem else ''
            
            img_elem = item.find('img', class_='part-group__image')
            image_url = img_elem.get('src') if img_elem else ''
            
            return {
                'id': group_id,
                'name': name,
                'url': url,
                'description': description,
                'image_url': image_url,
                'parts': []
            }
        except Exception as e:
            print(f"Error parsing part group: {str(e)}")
            return None
    
    def get_part_group_parts(self, part_group, variant_code):
        """Get parts for a part group"""
        print(f"\n      {'˙'*50}")
        print(f"PARTS FOR {part_group['name']}")
        print(f"      {'˙'*50}")
        
        soup = self.get_page(part_group['url'])
        if not soup:
            return []
        
        parts = []
        part_rows = soup.find_all('tr', class_='items-list__row')
        
        for row in part_rows:
            part_data = self.parse_part_item(row)
            if part_data:
                parts.append(part_data)
                print(f"{part_data['number']} - {part_data['name']}")
        
        print(f"Total: {len(parts)} parts")
        return parts
    
    def parse_part_item(self, row):
        """Parse part details from table row"""
        try:
            # Get data-item attribute
            data_item_str = row.get('data-item', '{}')
            data_item = json.loads(data_item_str)
            
            # Extract part number
            number_elem = row.find('div', class_='items-list__number')
            if not number_elem:
                number_elem = row.find('p', class_='items-list__number')
            number = number_elem.text.strip() if number_elem else data_item.get('number', '')
            
            # Extract part name
            name_elem = row.find('span', class_='items-list__name')
            name = name_elem.text.strip() if name_elem else data_item.get('name', '')
            
            # Extract description
            desc_elem = row.find('p', class_='items-list__description')
            description = desc_elem.text.strip() if desc_elem else data_item.get('itemsset_description', '')
            
            # Extract ref
            ref_elem = row.find('div', class_='items-list__ref')
            ref = ref_elem.text.strip() if ref_elem else data_item.get('ref', '')
            
            return {
                'number': number,
                'name': name,
                'ref': ref,
                'description': description,
                'quantity': data_item.get('quantity', ''),
                'manufacturer': data_item.get('manufacturer', ''),
                'original_item_id': data_item.get('original_item_id', '')
            }
        except Exception as e:
            print(f"Error parsing part: {str(e)}")
            return None
    
    def crawl_all(self, max_models=None, max_frames=None, max_variants=None, max_part_groups=None, crawl_parts=True):
        models = self.get_models()
        
        if max_models:
            models = models[:max_models]
            print(f"\nLimiting to {max_models} models")
        
        total_stats = {
            'models': 0,
            'frames': 0,
            'variants': 0,
            'part_groups': 0,
            'parts': 0
        }
        
        for i, model in enumerate(models, 1):
            print(f"\n{'='*80}")
            print(f"MODEL {i}/{len(models)}: {model['name']}")
            print(f"{'='*80}")
            
            frames = self.get_model_frames(model)
            model['frames'] = frames
            total_stats['models'] += 1
            total_stats['frames'] += len(frames)

            
            
            if max_frames:
                frames = frames[:max_frames]
            
            for j, frame in enumerate(frames, 1):
                variants = self.get_frame_variants(frame, model['name'])
                frame['variants'] = variants
                total_stats['variants'] += len(variants)
                
                if max_variants:
                    variants = variants[:max_variants]
                total_vars = len(variants)
                for k, variant in enumerate(variants, 1):
                    part_groups = self.get_variant_part_groups(variant, model['name'], frame['name'], k, total_vars)
                    variant['part_groups'] = part_groups
                    total_stats['part_groups'] += len(part_groups)
                    
                    if max_part_groups:
                        part_groups = part_groups[:max_part_groups]
                    
                    if crawl_parts:
                        total_pg = len(part_groups)
                        for l, part_group in enumerate(part_groups, 1):
                            print(f"\n      [PART GROUP {l}/{total_pg}]")
                            parts = self.get_part_group_parts(part_group, variant['code'])
                            part_group['parts'] = parts
                            total_stats['parts'] += len(parts)
            backup_filename = f'backup_model_{i}.json'
            self.save_backup({
                'brand': 'Toyota',
                'statistics': total_stats,
                'current_model': i,
                'total_models': len(models),
                'models': models[:i]
            }, backup_filename)
            print(f"\nBackup saved: {backup_filename}")
                
        result = {
            'brand': 'Toyota',
            'statistics': total_stats,
            'models': models
        }
        
        return result
    
    
    def save_results(self, results, filename):
        """Save results to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n{'='*80}")
        print(f"✓ Saved to: {filename}")
        print(f"{'='*80}")

    def save_backup(self, results, filename):
        """Save backup without printing banner"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    
    def print_summary(self, results):
        """Print crawl summary"""
        stats = results['statistics']
        print("\n" + "="*80)
        print("CRAWL SUMMARY")
        print("="*80)
        print(f"Brand: {results['brand']}")
        print(f"Crawl Date: {results['crawl_date']}")
        print(f"\nStatistics:")
        print(f"  Models: {stats['models']}")
        print(f"  Frames: {stats['frames']}")
        print(f"  Variants: {stats['variants']}")
        print(f"  Part Groups: {stats['part_groups']}")
        print(f"  Parts: {stats['parts']}")
        

if __name__ == "__main__":
    crawler = MegazipCrawler()
    results = crawler.crawl_all()
    crawler.save_results(results, 'toyota.json')
    crawler.print_summary(results)
    
    