import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import os

class PartsouqCrawler:
    def __init__(self):
        # Setup undetected Chrome để bypass Cloudflare
        options = uc.ChromeOptions()
        # options.add_argument('--headless=new')  # Uncomment để chạy ngầm
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = uc.Chrome(options=options, version_main=None)
        self.base_url = "https://partsouq.com"
    
    def load_json(self, filename):
        """Load data from JSON file"""
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    def get_all_brands(self):
        """Crawl all brand links from homepage"""
        
        try:
            self.driver.get(self.base_url)
            
            # Chờ Cloudflare check
            time.sleep(8)
            
            # Wait for brand container
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.ID, "make-icons")))
            
            # Find all brand links
            brand_elements = self.driver.find_elements(By.CSS_SELECTOR, "#make-icons .item a")
            
            brands = []
            for element in brand_elements:
                try:
                    brand_name = element.find_element(By.CLASS_NAME, "shop-title").text
                    brand_href = element.get_attribute("href")
                    
                    brands.append({
                        "brand": brand_name,
                        "href": brand_href
                    })
                    
                    print(f"Found: {brand_name} - {brand_href}")
                    
                except Exception as e:
                    print(f"Lỗi khi parse brand: {e}")
                    continue
            
            return brands
            
        except Exception as e:
            print(f"Lỗi khi crawl brands: {e}")
            return []
    
    def get_car_types(self, brand_url):
        """Get all car types/models for a brand"""
        print(f"\n Đang crawl car types từ: {brand_url}")
        
        try:
            self.driver.get(brand_url)
            
            # Chờ Cloudflare check
            time.sleep(6)
            
            # Wait for panel to load
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-heading")))
            
            car_types = []
            seen_urls = set()
            
            # Tìm tất cả links có href chứa '/catalog/genuine/pick'
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/catalog/genuine/pick']")
            
            print(f" Tìm thấy {len(all_links)} links...")
            
            for link in all_links:
                try:
                    car_type = link.text.strip()
                    car_href = link.get_attribute("href")
                    
                    if car_type and car_href and car_href not in seen_urls:
                        car_type = car_type.replace('\n', ' ').strip()
                        
                        car_types.append({
                            "car_type": car_type,
                            "href": car_href
                        })
                        
                        seen_urls.add(car_href)
                        print(f"   {car_type}")
                        
                except Exception as e:
                    continue
            
            return car_types
            
        except Exception as e:
            print(f"   Lỗi khi crawl car types: {e}")
            try:
                self.driver.save_screenshot("error_screenshot.png")
            except:
                pass
            return []
    
    def get_models(self, car_type_url):
        """Get all models for a car type"""
        print(f"\n     Đang crawl models từ: {car_type_url}")
        
        try:
            self.driver.get(car_type_url)
            
            # Chờ Cloudflare
            time.sleep(5)
            
            # Wait for table to load
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".search-result-vin")))
            
            models = []
            seen_urls = set()
            
            # Tìm tất cả rows trong table (bỏ qua header row)
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".search-result-vin tbody tr:not(:first-child)")
            
            print(f"       Tìm thấy {len(rows)} models...")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        name = cells[0].text.strip()
                        description = cells[1].text.strip()
                        model = cells[2].text.strip()
                        options = cells[3].text.strip()
                        prod_period = cells[4].text.strip()
                        
                        # Lấy URL từ Model column
                        model_link = cells[2].find_element(By.TAG_NAME, "a")
                        model_url = model_link.get_attribute("href")
                        
                        if model and model_url and model_url not in seen_urls:
                            models.append({
                                "name": name,
                                "description": description,
                                "model": model,
                                "options": options,
                                "prod_period": prod_period,
                                "url": model_url
                            })
                            
                            seen_urls.add(model_url)
                            print(f"       {model} - {description}")
                            
                except Exception as e:
                    print(f"       Lỗi parse row: {e}")
                    continue
            
            return models
            
        except Exception as e:
            print(f"       Lỗi khi crawl models: {e}")
            try:
                self.driver.save_screenshot("error_models.png")
                print("      Đã lưu screenshot: error_models.png")
            except:
                pass
            return []
    
    def get_categories_and_titles(self, model_url):
        """Get all categories and their titles/diagrams"""
        print(f"\n        Đang crawl categories từ: {model_url}")
        
        try:
            self.driver.get(model_url)
            
            # Chờ Cloudflare
            print("         Đang chờ Cloudflare...")
            time.sleep(5)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".vehicle-tg")))
            
            categories = []
            
            # BƯỚC 1: Crawl DEFAULT CATEGORY
            try:
                default_category_name = self.driver.find_element(By.CSS_SELECTOR, "h2.current-category").text.strip()
                default_category_name = default_category_name.replace(" Diagrams", "").strip()
                
                print(f"         Default Category: {default_category_name}")
                
                # Crawl titles đang hiển thị
                default_titles = self.get_titles_only()
                
                categories.append({
                    "category": default_category_name,
                    "url": model_url,
                    "titles": default_titles
                })
                
                print(f"             {len(default_titles)} titles found")
                
            except Exception as e:
                print(f"         Không crawl được default category: {e}")
            
            # BƯỚC 2: Thu thập danh sách CHILD CATEGORIES
            category_info_list = []
            seen_urls = set()
            
            category_rows = self.driver.find_elements(By.CSS_SELECTOR, ".vehicle-tg tbody tr")
            print(f"         Tìm thấy {len(category_rows)} rows trong sidebar")
            
            for idx, row in enumerate(category_rows):
                try:
                    # Kiểm tra xem row này có link không
                    links = row.find_elements(By.TAG_NAME, "a")
                    
                    if links:
                        # Row có link - đây là category có thể click
                        link = links[0]
                        category_name = link.text.strip()
                        category_url = link.get_attribute("href")
                        
                        if category_name and category_url and category_url not in seen_urls:
                            category_info_list.append({
                                "name": category_name,
                                "url": category_url
                            })
                            seen_urls.add(category_url)
                            print(f"         Found Category: {category_name}")
                    else:
                        # Row không có link - parent category
                        try:
                            cell_text = row.find_element(By.TAG_NAME, "td").text.strip()
                            if cell_text:
                                print(f"         Parent: {cell_text}")
                        except:
                            pass
                        
                except Exception as e:
                    print(f"         Lỗi parse row {idx}: {e}")
                    continue
            
            print(f"         Tổng số child categories: {len(category_info_list)}")
            
            # BƯỚC 3: Crawl titles cho từng child category
            for idx, cat_info in enumerate(category_info_list, 1):
                print(f"\n        [{idx}/{len(category_info_list)}]  Crawling: {cat_info['name']}")
                
                # Navigate to category
                self.driver.get(cat_info['url'])
                time.sleep(4)
                
                # Get titles (không lấy parts)
                titles = self.get_titles_only()
                
                categories.append({
                    "category": cat_info['name'],
                    "url": cat_info['url'],
                    "titles": titles
                })
                
                print(f"             {len(titles)} titles found")
            
            return categories
        
        except Exception as e:
            print(f"       Lỗi khi crawl categories: {e}")
            try:
                self.driver.save_screenshot("error_categories.png")
            except:
                pass
            return []
        
    def get_titles_only(self):
        """Get all titles from current page WITHOUT crawling parts"""
        try:
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".thumbnail")))
            
            titles = []
            seen_urls = set()
            
            # Find all diagram thumbnails
            thumbnails = self.driver.find_elements(By.CSS_SELECTOR, ".thumbnail")
            
            print(f"             Tìm thấy {len(thumbnails)} thumbnails")
            
            for thumb in thumbnails:
                try:
                    # Get title from caption h5 > a
                    caption = thumb.find_element(By.CSS_SELECTOR, ".caption h5 a")
                    title_text = caption.text.strip()
                    title_url = caption.get_attribute("href")
                    
                    if title_text and title_url and title_url not in seen_urls:
                        titles.append({
                            "title": title_text,
                            "url": title_url
                        })
                        
                        seen_urls.add(title_url)
                        print(f"              {title_text}")
                        
                except Exception as e:
                    continue
            
            return titles
            
        except Exception as e:
            print(f"           Lỗi khi crawl titles: {e}")
            return []
    
    def save_to_json(self, data, filename):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n Đã lưu vào file: {filename}")
    
    def close(self):
        """Close browser"""
        self.driver.quit()


# Main execution - RESUME FROM BACKUP
if __name__ == "__main__":
    crawler = PartsouqCrawler()
    
    # ⚙️ CẤU HÌNH - ĐIỀN THỦ CÔNG
    TARGET_BRAND = "Toyota"
    RESUME_FROM_BACKUP = "Toyota_CT1_Model1.json"  #  Điền tên file backup gần nhất
    
    #  Parse tên file để lấy vị trí
    # Format: Brand_CTx_Modely.json
    try:
        filename = RESUME_FROM_BACKUP.replace('.json', '')
        parts = filename.split('_')
        
        ct_part = [p for p in parts if p.startswith('CT')][0]
        model_part = [p for p in parts if p.startswith('Model')][0]
        
        START_CT = int(ct_part.replace('CT', ''))
        START_MODEL = int(model_part.replace('Model', ''))
        
        print(f"\n📍 Parse từ filename: CT={START_CT}, Model={START_MODEL}")
        print(f"▶️  Sẽ resume từ CT{START_CT} Model{START_MODEL + 1}")
        
    except Exception as e:
        print(f"\n❌ Lỗi parse filename: {e}")
        print(f"Format đúng: Brand_CTx_Modely.json")
        exit(1)
    
    try:
        
        # Load backup data
        if os.path.exists(RESUME_FROM_BACKUP):
            print(f"\n✅ Đã tìm thấy file backup: {RESUME_FROM_BACKUP}")
            target_brand_data = crawler.load_json(RESUME_FROM_BACKUP)[0]
            print(f"📊 Đã có {len(target_brand_data.get('car_types', []))} car types trong backup")
        else:
            print(f"\n❌ Không tìm thấy file: {RESUME_FROM_BACKUP}")
            exit(1)
        
        # Get all car types from brand page
        print(f"\n🔍 Đang lấy danh sách tất cả car types...")
        all_car_types = crawler.get_car_types(target_brand_data['href'])
        print(f"📋 Tổng số car types: {len(all_car_types)}")
        
        if START_CT > len(all_car_types):
            print(f"\n❌ Car type #{START_CT} không tồn tại!")
            print(f"Chỉ có {len(all_car_types)} car types")
            exit(1)
        
        # Crawl từ car type START_CT trở đi
        for ct_idx in range(START_CT - 1, len(all_car_types)):
            car_type = all_car_types[ct_idx]
            actual_ct_idx = ct_idx + 1  # Index thực (1-based)
            
            print(f"\n{'='*60}")
            print(f"🚗 [{actual_ct_idx}/{len(all_car_types)}] Car Type: {car_type['car_type']}")
            print(f"{'='*60}")
            
            try:
                # Get models
                models = crawler.get_models(car_type['href'])
                
                # ⭐ XỬ LÝ 2 TRƯỜNG HỢP
                if actual_ct_idx == START_CT:
                    # Đang ở giữa car type → Tìm car_type_data trong backup
                    car_type_data = None
                    for ct in target_brand_data['car_types']:
                        if ct['car_type'] == car_type['car_type']:
                            car_type_data = ct
                            break
                    
                    if not car_type_data:
                        # Chưa có trong backup → tạo mới
                        car_type_data = {
                            "car_type": car_type['car_type'],
                            "href": car_type['href'],
                            "models": []
                        }
                        target_brand_data['car_types'].append(car_type_data)
                    
                    # Bắt đầu từ model tiếp theo
                    start_model_idx = START_MODEL  # Đã crawl xong model này rồi
                    print(f"⏩ Bỏ qua {start_model_idx} models đã crawl")
                else:
                    # Car type mới hoàn toàn
                    car_type_data = {
                        "car_type": car_type['car_type'],
                        "href": car_type['href'],
                        "models": []
                    }
                    target_brand_data['car_types'].append(car_type_data)
                    start_model_idx = 0  # Crawl từ đầu
                
                if not models:
                    print(f"   ⚠️  Không tìm thấy models")
                    continue
                
                print(f"  📝 Tìm thấy {len(models)} models")
                
                # ⭐ Crawl từ model start_model_idx trở đi
                for model_idx in range(start_model_idx, len(models)):
                    model = models[model_idx]
                    actual_model_idx = model_idx + 1
                    
                    print(f"\n  🔧 [{actual_model_idx}/{len(models)}] Model: {model['name']}")
                    
                    try:
                        # Get TẤT CẢ categories và titles
                        categories = crawler.get_categories_and_titles(model['url'])
                        
                        model_data = {
                            "name": model['name'],
                            "url": model['url'],
                            "categories": categories
                        }
                        
                        car_type_data['models'].append(model_data)
                        
                        # Thống kê
                        total_titles = sum(len(cat['titles']) for cat in categories)
                        print(f"    ✅ {len(categories)} categories, {total_titles} titles")
                        
                        # ⭐ LƯU BACKUP SAU MỖI MODEL
                        backup_filename = f"{TARGET_BRAND}_CT{actual_ct_idx}_Model{actual_model_idx}.json"
                        crawler.save_to_json([target_brand_data], backup_filename)
                        
                    except Exception as e:
                        print(f"    ❌ Lỗi crawl model {model['name']}: {e}")
                        continue
                
                # ⭐ Reset start_model_idx cho car type tiếp theo
                start_model_idx = 0
                
            except Exception as e:
                print(f"   ❌ Lỗi crawl car type: {e}")
                continue
        
        # Save final result
        crawler.save_to_json([target_brand_data], f"{TARGET_BRAND}_Complete.json")
        
        # Thống kê tổng kết
        total_car_types = len(target_brand_data['car_types'])
        total_models = sum(len(ct['models']) for ct in target_brand_data['car_types'])
        total_categories = sum(
            len(model['categories']) 
            for ct in target_brand_data['car_types'] 
            for model in ct['models']
        )
        total_titles = sum(
            len(cat['titles'])
            for ct in target_brand_data['car_types']
            for model in ct['models']
            for cat in model['categories']
        )
        
        
        print(f"{'='*80}")
        print(f"   - Car Types: {total_car_types}")
        print(f"   - Models: {total_models}")
        print(f"   - Categories: {total_categories}")
        print(f"   - Titles: {total_titles}")
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔒 Đóng browser...")
        crawler.close()
    
    print("\n✨ HOÀN THÀNH!")
    
    