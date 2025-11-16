import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import os
from multiprocessing import Process, Queue
import queue

class PartsouqHTMLSaver:
    def __init__(self):
        # Setup undetected Chrome 
        options = uc.ChromeOptions()
        # options.add_argument('--headless=new')  
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = uc.Chrome(options=options, version_main=None)
        self.base_url = "https://partsouq.com"
        
        # Tạo thư mục lưu HTML
        self.html_folder = 'html_sources'
        os.makedirs(self.html_folder, exist_ok=True)
        
        # Thư mục backup
        self.backup_folder = 'backups'
        os.makedirs(self.backup_folder, exist_ok=True)
        
        # Tracking folder đã dùng để tránh trùng
        self.used_folders = {}
        self.current_model_folder = None
    
    def load_json(self, filename):
        """Load data from JSON file"""
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_json(self, data, filename):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu file: {filename}")
    
    def save_backup(self, data, brand_name, car_type_idx, model_idx, worker_id=""):
        """Lưu backup sau mỗi model"""
        safe_brand = self._safe_filename(brand_name)
        
        # Thêm worker_id để tránh conflict
        if worker_id:
            backup_filename = f"{safe_brand}_CarType{car_type_idx}_Model{model_idx}_W{worker_id}.json"
        else:
            backup_filename = f"{safe_brand}_CarType{car_type_idx}_Model{model_idx}.json"
        
        backup_path = os.path.join(self.backup_folder, backup_filename)
        
        self.save_json(data, backup_path)
        print(f"💾 BACKUP: {backup_path}")
    
    def set_current_model_folder(self, brand, car_type, model, model_idx):
        """Set folder cho model hiện tại"""
        base_model_folder = os.path.join(
            self.html_folder,
            self._safe_filename(brand),
            self._safe_filename(car_type),
            f"{self._safe_filename(model)}_Model{model_idx}" 
        )
        
        self.current_model_folder = base_model_folder
        os.makedirs(base_model_folder, exist_ok=True)
        print(f"  📁 Model folder: {self.current_model_folder}")
    
    def _get_unique_folder(self, base_path):
        """Tạo tên thư mục unique nếu bị trùng"""
        if base_path not in self.used_folders:
            if not os.path.exists(base_path):
                self.used_folders[base_path] = base_path
                return base_path
            else:
                counter = 1
                while True:
                    new_path = f"{base_path}{counter}"
                    if not os.path.exists(new_path):
                        self.used_folders[base_path] = new_path
                        return new_path
                    counter += 1
        
        return self.used_folders[base_path]
    
    def _safe_filename(self, name):
        """Chuyển tên thành tên file an toàn"""
        safe = name.replace('/', '').replace('\\', '').replace(':', '_')
        safe = safe.replace('*', '').replace('?', '').replace('"', '_')
        safe = safe.replace('<', '').replace('>', '').replace('|', '_')
        safe = safe.replace(' ', '_').strip()
        
        if len(safe) > 100:
            safe = safe[:100]
        
        return safe
    
    def save_html(self, url, brand, car_type, model, category, title):
        """Truy cập URL, lưu HTML VÀ crawl parts"""
        try:
            print(f"      🌐 Đang truy cập: {url}")
            self.driver.get(url)
            
            # Chờ Cloudflare
            print(f"      ⏳ Chờ Cloudflare...")
            time.sleep(3)
            
            # Wait for page load
            print(f"      ⏳ Chờ load trang...")
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".table-bordered-1")))
            
            # Lấy HTML source
            html_content = self.driver.page_source
            
            if not self.current_model_folder:
                raise Exception("Chưa set current_model_folder!")
            
            # Tạo đường dẫn đầy đủ
            folder_path = os.path.join(
                self.current_model_folder,
                self._safe_filename(category)
            )
            os.makedirs(folder_path, exist_ok=True)
            
            filename = self._safe_filename(title) + '.html'
            filepath = os.path.join(folder_path, filename)
            
            # Lưu HTML
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            relative_path = os.path.relpath(filepath, '.')
            print(f"      📄 HTML: {relative_path}")
            
            # CRAWL PARTS DATA
            print(f"      🔧 Đang parse parts...")
            parts = self._parse_parts()
            print(f"      ✅ Parts: {len(parts)} items")
            
            return relative_path, parts
            
        except Exception as e:
            print(f"      ❌ Lỗi save_html: {e}")
            return None, []
    
    def _parse_parts(self):
        """Parse parts"""
        try:
            parts = []
            
            tables = self.driver.find_elements(By.CSS_SELECTOR, ".table-bordered-1")
            if not tables:
                print("     ⚠️  Không tìm thấy table parts")
                return []
            
            table = tables[0]
            
            # ĐỌC HEADERS
            try:
                headers = table.find_elements(By.CSS_SELECTOR, "thead tr th")
                header_names = []
                
                for h in headers:
                    header_text = h.text.strip()
                    if header_text:
                        safe_name = header_text.lower().replace(' ', '').replace('-', '')
                        safe_name = safe_name.replace('/', '_').replace('(', '').replace(')', '')
                        header_names.append(safe_name)
                    else:
                        header_names.append(f"col_{len(header_names)}")
                
                print(f"     📋 Headers ({len(header_names)} cột): {header_names}")
                
                if not header_names:
                    print("     ❌ Không có headers!")
                    return []
                
            except Exception as e:
                print(f"     ❌ Lỗi đọc headers: {e}")
                return []
            
            # PARSE ROWS
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr.part-search-tr")
            
            if not rows:
                all_rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                rows = [row for row in all_rows if not row.find_elements(By.TAG_NAME, "th")]
            
            print(f"     🔍 Tìm thấy {len(rows)} rows")
            
            for row_idx, row in enumerate(rows, 1):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 1:
                        continue
                    
                    part_data = {}
                    
                    for col_idx, cell in enumerate(cells):
                        if col_idx < len(header_names):
                            field_name = header_names[col_idx]
                        else:
                            field_name = f"col_{col_idx}"
                        
                        links = cell.find_elements(By.TAG_NAME, "a")
                        if links:
                            value = links[0].text.strip()
                        else:
                            value = cell.text.strip()
                        
                        if value:
                            part_data[field_name] = value
                    
                    if part_data:
                        parts.append(part_data)
                        
                        if row_idx == 1:
                            print(f"     ✅ Sample: {part_data}")
                    
                except Exception as e:
                    if row_idx <= 2:
                        print(f"     ⚠️  Lỗi row {row_idx}: {e}")
                    continue
            
            print(f"     ✅ Crawled {len(parts)} parts")
            return parts
            
        except Exception as e:
            print(f"     ❌ Lỗi parse parts: {e}")
            return []
    
    def close(self):
        """Close browser"""
        self.driver.quit()


# ⭐ WORKER FUNCTION - Mỗi process chạy function này
def worker_crawl_model(worker_id, model_data, brand_name, car_type_name, car_type_idx, model_idx, output_queue):
    """
    Worker function để crawl 1 model
    Mỗi worker chạy trong process riêng với browser riêng
    """
    print(f"\n🔵 [Worker {worker_id}] Bắt đầu crawl Model {model_idx}: {model_data['name']}")
    
    try:
        # Tạo instance crawler riêng cho worker này
        saver = PartsouqHTMLSaver()
        
        model_name = model_data['name']
        
        # SET FOLDER CHO MODEL
        saver.set_current_model_folder(brand_name, car_type_name, model_name, model_idx)
        
        model_start_time = time.time()
        
        # Crawl tất cả categories trong model này
        for category in model_data.get('categories', []):
            category_name = category['category']
            print(f"\n    [W{worker_id}] 📁 Category: {category_name}")
            print(f"    [W{worker_id}] 📋 Titles: {len(category.get('titles', []))}")
            
            # Loop through titles
            for idx, title in enumerate(category.get('titles', []), 1):
                title_name = title['title']
                title_url = title['url']
                
                print(f"\n      [W{worker_id}] [{idx}/{len(category['titles'])}] 📝 {title_name}")
                
                # Lưu HTML VÀ crawl parts
                html_file, parts = saver.save_html(
                    title_url,
                    brand_name,
                    car_type_name,
                    model_name,
                    category_name,
                    title_name
                )
                
                if html_file:
                    title['html_file'] = html_file
                    title['parts'] = parts
                else:
                    title['html_file'] = None
                    title['parts'] = []
        
        model_elapsed = time.time() - model_start_time
        print(f"\n  [W{worker_id}] ⏱️  Hoàn thành Model {model_name} trong {model_elapsed/60:.1f} phút")
        
        # Đóng browser
        saver.close()
        
        # Trả kết quả về main process qua queue
        output_queue.put({
            'worker_id': worker_id,
            'car_type_idx': car_type_idx,
            'model_idx': model_idx,
            'model_data': model_data,
            'success': True
        })
        
    except Exception as e:
        print(f"\n❌ [Worker {worker_id}] Lỗi: {e}")
        import traceback
        traceback.print_exc()
        
        output_queue.put({
            'worker_id': worker_id,
            'car_type_idx': car_type_idx,
            'model_idx': model_idx,
            'model_data': None,
            'success': False,
            'error': str(e)
        })


# ⭐ MAIN FUNCTION - Quản lý parallel crawling
def parallel_crawl(input_file, output_file, num_workers=2):
    """
    Crawl song song với số lượng workers tùy chỉnh
    num_workers: Số lượng browser chạy đồng thời (2-3 khuyến nghị)
    """
    
    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Copy sang output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã copy {input_file} → {output_file}")
    
    # Tạo danh sách tất cả models cần crawl
    model_queue = []
    
    for brand in data:
        brand_name = brand['brand']
        
        for car_type_idx, car_type in enumerate(brand.get('car_types', []), 1):
            car_type_name = car_type['car_type']
            
            for model_idx, model in enumerate(car_type.get('models', []), 1):
                model_queue.append({
                    'brand_name': brand_name,
                    'car_type_name': car_type_name,
                    'car_type_idx': car_type_idx,
                    'model_idx': model_idx,
                    'model_data': model
                })
    
    print(f"\n📊 Tổng số models cần crawl: {len(model_queue)}")
    print(f"🔢 Số workers: {num_workers}")
    print(f"⏱️  Ước tính thời gian: {len(model_queue) / num_workers:.1f}x nhanh hơn\n")
    
    # Queue để nhận kết quả từ workers
    output_queue = Queue()
    
    # Tracking
    active_processes = []
    completed = 0
    failed = 0
    
    # Crawl từng batch
    model_idx_in_queue = 0
    
    while model_idx_in_queue < len(model_queue) or active_processes:
        
        # Start workers cho batch mới (nếu còn slot trống)
        while len(active_processes) < num_workers and model_idx_in_queue < len(model_queue):
            
            task = model_queue[model_idx_in_queue]
            worker_id = model_idx_in_queue + 1
            
            print(f"\n🚀 Khởi động Worker {worker_id} cho Model: {task['model_data']['name']}")
            
            # Tạo process mới
            p = Process(
                target=worker_crawl_model,
                args=(
                    worker_id,
                    task['model_data'],
                    task['brand_name'],
                    task['car_type_name'],
                    task['car_type_idx'],
                    task['model_idx'],
                    output_queue
                )
            )
            
            p.start()
            active_processes.append({
                'process': p,
                'worker_id': worker_id,
                'task': task
            })
            
            model_idx_in_queue += 1
        
        # Check xem có worker nào hoàn thành chưa
        time.sleep(2)  # Đợi 2s trước khi check
        
        # Thu thập kết quả từ queue (non-blocking)
        try:
            while True:
                result = output_queue.get_nowait()
                
                if result['success']:
                    print(f"\n✅ Worker {result['worker_id']} hoàn thành!")
                    
                    # Cập nhật data với kết quả mới
                    for brand in data:
                        for car_type in brand.get('car_types', []):
                            for model in car_type.get('models', []):
                                if model['name'] == result['model_data']['name']:
                                    model.update(result['model_data'])
                                    break
                    
                    # Lưu backup
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    completed += 1
                else:
                    print(f"\n❌ Worker {result['worker_id']} thất bại: {result.get('error', 'Unknown')}")
                    failed += 1
                
                print(f"\n📊 Tiến độ: {completed}/{len(model_queue)} hoàn thành, {failed} thất bại, {len(active_processes)} đang chạy")
                
        except queue.Empty:
            pass
        
        # Loại bỏ processes đã kết thúc
        active_processes = [p for p in active_processes if p['process'].is_alive()]
    
    # Chờ tất cả processes kết thúc
    for p_info in active_processes:
        p_info['process'].join()
    
    print(f"\n{'='*60}")
    print(f"✨ HOÀN THÀNH!")
    print(f"   ✅ Thành công: {completed}")
    print(f"   ❌ Thất bại: {failed}")
    print(f"{'='*60}")


# Main execution
if __name__ == "__main__":
    
    # ⚙️ CẤU HÌNH
    INPUT_FILE = "Nissan_Progress_CT8.json"  # File input
    OUTPUT_FILE = "Nissan.json"   # File output
    NUM_WORKERS = 3  #  Số browser chạy đồng thời 
    
    print(f"📥 Input: {INPUT_FILE}")
    print(f"📤 Output: {OUTPUT_FILE}")
    print(f"🔢 Workers: {NUM_WORKERS}")
    print("="*60)
    
    parallel_crawl(INPUT_FILE, OUTPUT_FILE, NUM_WORKERS)