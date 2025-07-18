import os
import time
import json
import requests
from datetime import datetime, timedelta
import schedule
from plyer import notification
import logging
import xml.etree.ElementTree as ET
import re
from urllib.parse import quote
from config import categories,query_mapping, default_config

class ArxivMonitor:
    def __init__(self, config_file="arxiv_config.json"):
        """
        初始化arXiv监控器
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logging()
        self.base_url = "http://export.arxiv.org/api/query"
        
    def load_config(self):
        """加载配置文件"""
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    config["search_queries"] = default_config["search_queries"]
                # 合并默认配置和用户配置
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                
                # 如果没有query_last_check字段，创建一个空的字典
                if "query_last_check" not in config:
                    config["query_last_check"] = {}
                
                return config
            except Exception as e:
                print(f"配置文件加载失败，使用默认配置: {e}")
                return default_config
        else:
            # 创建默认配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('arxiv_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_folder_name_for_query(self, query):
        """
        根据搜索查询生成文件夹名称
        
        Args:
            query: 搜索查询字符串
            
        Returns:
            安全的文件夹名称
        """
        # 如果有预定义映射，使用映射
        if query in query_mapping:
            return query_mapping[query]
        
        # 否则生成安全的文件夹名
        safe_name = re.sub(r'[^\w\s-]', '', query)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        safe_name = safe_name[:50].strip('_')
        
        # 如果是类别查询，添加前缀
        if query.startswith('cat:'):
            return f"category_{safe_name}"
        else:
            return f"keywords_{safe_name}"
    
    def create_download_directory(self, query=None):
        """
        创建下载目录
        
        Args:
            query: 可选，特定查询的目录
        """
        base_path = self.config["download_path"]
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        if query and self.config.get("organize_by_query", True):
            folder_name = self.get_folder_name_for_query(query)
            query_path = os.path.join(base_path, folder_name)
            if not os.path.exists(query_path):
                os.makedirs(query_path)
                self.logger.info(f"创建查询目录: {query_path}")
            return query_path
        
        return base_path
    
    def search_papers_direct_api(self, query, max_results=10):
        """
        直接使用arXiv API搜索论文
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            论文列表
        """
        try:
            # 构建查询参数
            params = {
                'search_query': query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            # 发送请求
            self.logger.info(f"正在请求arXiv API: {query}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 解析XML响应
            root = ET.fromstring(response.content)
            
            # 定义命名空间
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            papers = []
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                try:
                    # 提取论文信息
                    paper_id = entry.find('atom:id', namespaces).text.split('/')[-1].split('v')[0]
                    title = entry.find('atom:title', namespaces).text.strip()
                    summary = entry.find('atom:summary', namespaces).text.strip()
                    
                    # 提取作者
                    authors = []
                    for author in entry.findall('atom:author', namespaces):
                        name = author.find('atom:name', namespaces)
                        if name is not None:
                            authors.append(name.text)
                    
                    # 提取发布日期
                    published_str = entry.find('atom:published', namespaces).text
                    published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    
                    # 提取PDF链接
                    pdf_url = ""
                    for link in entry.findall('atom:link', namespaces):
                        if link.get('title') == 'pdf':
                            pdf_url = link.get('href')
                            break
                    
                    # 提取类别
                    categories = []
                    for category in entry.findall('atom:category', namespaces):
                        term = category.get('term')
                        if term:
                            categories.append(term)
                    
                    # 如果没有找到PDF链接，构造一个
                    if not pdf_url:
                        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
                    
                    papers.append({
                        'id': paper_id,
                        'title': title,
                        'authors': authors,
                        'summary': summary,
                        'published': published,
                        'pdf_url': pdf_url,
                        'categories': categories,
                        'query': query  # 添加查询信息
                    })
                    
                except Exception as e:
                    self.logger.warning(f"解析论文条目时出错: {e}")
                    continue
            
            self.logger.info(f"成功获取 {len(papers)} 篇论文")
            return papers
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求arXiv API失败: {e}")
            return []
        except ET.ParseError as e:
            self.logger.error(f"解析XML响应失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"搜索论文时出错: {e}")
            return []
    
    def search_papers(self, query, max_results=10):
        """
        搜索论文 - 主入口
        """
        return self.search_papers_direct_api(query, max_results)
    
    def download_paper(self, paper):
        """
        下载论文PDF到对应的查询文件夹
        
        Args:
            paper: 论文信息字典
            
        Returns:
            下载成功返回True，否则返回False
        """
        try:
            if not paper['pdf_url']:
                self.logger.warning(f"论文 {paper['id']} 没有PDF链接")
                return False
            
            # 获取对应查询的下载目录
            download_dir = self.create_download_directory(paper.get('query'))
            
            # 创建安全的文件名
            safe_title = re.sub(r'[^\w\s-]', '', paper['title'])
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            safe_title = safe_title[:100].strip('-')
            filename = f"{paper['id']}_{safe_title}.pdf"
            filepath = os.path.join(download_dir, filename)
            
            # 检查文件是否已存在
            if os.path.exists(filepath):
                self.logger.info(f"文件已存在: {filename}")
                return True
            
            # 下载PDF
            self.logger.info(f"正在下载到 {os.path.basename(download_dir)}: {paper['title'][:50]}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # 尝试下载
            response = requests.get(paper['pdf_url'], headers=headers, timeout=60)
            response.raise_for_status()
            
            # 检查是否真的是PDF文件
            if not response.content.startswith(b'%PDF'):
                self.logger.warning(f"下载的文件不是有效的PDF: {paper['id']}")
                return False
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"成功下载: {filename} ({len(response.content)} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"下载论文失败 {paper['id']}: {e}")
            return False
    
    def filter_new_papers(self, papers, query):
        """
        筛选新论文（未下载过的，基于特定查询的时间）
        
        Args:
            papers: 论文列表
            query: 当前查询
            
        Returns:
            新论文列表
        """
        downloaded_ids = set(self.config["downloaded_papers"])
        new_papers = []
        
        for paper in papers:
            if paper['id'] not in downloaded_ids:
                # 如果是首次运行，获取最近24小时的论文
                if self.config.get("first_run", True):
                    cutoff_time = datetime.now() - timedelta(days=1000)
                    if paper['published'].replace(tzinfo=None) > cutoff_time:
                        print(f"因为首次运行获取到的论文（查询: {query}）")
                        new_papers.append(paper)
                else:
                    # 检查该查询的上次检查时间
                    query_last_check = self.config["query_last_check"].get(query)
                    if query_last_check:
                        try:
                            last_check = datetime.fromisoformat(query_last_check)
                            if paper['published'].replace(tzinfo=None) > last_check.replace(tzinfo=None):
                                print(f"因为在查询 '{query}' 的时间之后获取到的论文")
                                new_papers.append(paper)
                        except:
                            # 如果日期解析失败，就添加这篇论文
                            print(f"日期解析失败（查询: {query}）")
                            new_papers.append(paper)
                    else:
                        # 如果该查询没有检查记录，添加论文
                        print(f"直接添加论文（查询: {query}，无历史记录）")
                        new_papers.append(paper)
        
        return new_papers
    
    def send_notification(self, title, message):
        """发送系统通知"""
        try:
            notification.notify(
                title=title,
                message=message,
                timeout=10
            )
        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")
            # 如果通知失败，至少在控制台显示
            print(f"\n🔔 {title}: {message}")
    
    def test_arxiv_connection(self):
        """测试arxiv连接和API"""
        print("🔍 正在测试arXiv连接...")
        
        try:
            # 测试直接API调用
            test_query = "cat:cs.AI"
            papers = self.search_papers_direct_api(test_query, max_results=2)
            
            if papers:
                print(f"✅ arXiv API连接成功！获取到 {len(papers)} 篇论文")
                print(f"📄 测试论文: {papers[0]['title'][:80]}...")
                print(f"👥 作者: {', '.join(papers[0]['authors'][:2])}")
                print(f"📅 发布: {papers[0]['published'].strftime('%Y-%m-%d')}")
                return True
            else:
                print("❌ arXiv API连接失败")
                return False
                
        except Exception as e:
            print(f"❌ arXiv连接测试失败: {e}")
            return False
    
    def show_available_categories(self):
        """显示可用的arXiv分类"""
        
        print("\n📚 arXiv 主要分类目录:")
        print("=" * 80)
        
        for main_cat, subcats in categories.items():
            print(f"\n🏷️  {main_cat}")
            print("-" * 60)
            for cat_code, cat_name in subcats.items():
                print(f"   {cat_code:<15} {cat_name}")
    
    def check_for_new_papers(self):
        """检查新论文"""
        self.logger.info("开始检查新论文...")
        self.create_download_directory()
        
        # 如果是首次运行，提示用户
        if self.config.get("first_run", True):
            print("📢 这是首次运行，将下载最近24小时的论文作为演示")
        
        all_new_papers = []
        
        # 对每个搜索查询进行独立检查
        for query in self.config["search_queries"]:
            self.logger.info(f"搜索查询: {query}")
            papers = self.search_papers(query, self.config["max_results"])
            
            if papers:
                self.logger.info(f"查询 '{query}' 找到 {len(papers)} 篇论文")
                new_papers = self.filter_new_papers(papers, query)
                
                if new_papers:
                    self.logger.info(f"其中 {len(new_papers)} 篇是新论文")
                    all_new_papers.extend(new_papers)
                    
                    # 更新该查询的检查时间
                    self.config["query_last_check"][query] = datetime.now().isoformat()
                else:
                    self.logger.info("没有新论文")
                    # 即使没有新论文，也更新该查询的检查时间
                    self.config["query_last_check"][query] = datetime.now().isoformat()
            else:
                self.logger.warning(f"查询 '{query}' 没有返回结果")
                # 即使没有返回结果，也更新该查询的检查时间
                self.config["query_last_check"][query] = datetime.now().isoformat()
        
        # 去重（基于ID）
        unique_papers = {}
        for paper in all_new_papers:
            if paper['id'] not in unique_papers:
                unique_papers[paper['id']] = paper
        all_new_papers = list(unique_papers.values())
        
        if all_new_papers:
            print(f"\n🎯 找到 {len(all_new_papers)} 篇新论文，开始下载...")
        
        # 按查询分组显示下载进度
        papers_by_query = {}
        for paper in all_new_papers:
            query = paper.get('query', 'unknown')
            if query not in papers_by_query:
                papers_by_query[query] = []
            papers_by_query[query].append(paper)
        
        # 下载新论文
        successful_downloads = 0
        total_papers = len(all_new_papers)
        
        for query, papers in papers_by_query.items():
            folder_name = self.get_folder_name_for_query(query)
            print(f"\n📁 正在下载到文件夹: {folder_name} ({len(papers)} 篇)")
            
            for i, paper in enumerate(papers, 1):
                global_idx = successful_downloads + i
                print(f"📥 总进度: {global_idx}/{total_papers} | 当前文件夹: {i}/{len(papers)} - {paper['title'][:50]}...")
                
                if self.download_paper(paper):
                    self.config["downloaded_papers"].append(paper['id'])
                    successful_downloads += 1
        
        # 标记首次运行已完成
        if self.config.get("first_run", True):
            self.config["first_run"] = False
        
        # 保持全局检查时间兼容性
        self.config["last_check"] = datetime.now().isoformat()
        self.save_config()
        
        # 发送通知
        if successful_downloads > 0:
            message = f"成功下载了 {successful_downloads} 篇新论文!"
            self.send_notification("arXiv论文更新", message)
            self.logger.info(message)
            
            # 打印论文信息
            print("\n" + "="*60)
            print("🎉 新下载的论文汇总")
            print("="*60)
            
            for query, papers in papers_by_query.items():
                downloaded_papers = [p for p in papers if p['id'] in self.config["downloaded_papers"]]
                if downloaded_papers:
                    folder_name = self.get_folder_name_for_query(query)
                    print(f"\n📁 {folder_name} ({len(downloaded_papers)} 篇)")
                    print("-" * 40)
                    
                    for paper in downloaded_papers:
                        print(f"📄 {paper['title']}")
                        print(f"🆔 {paper['id']}")
                        print(f"👥 {', '.join(paper['authors'][:2])}" + 
                              (f" 等 {len(paper['authors'])} 人" if len(paper['authors']) > 2 else ""))
                        print(f"📅 {paper['published'].strftime('%Y-%m-%d')}")
                        print()
        else:
            self.logger.info("没有找到新论文")
            print("ℹ️  没有找到新论文")
    
    def toggle_organize_by_query(self):
        """切换是否按查询组织文件夹"""
        current = self.config.get("organize_by_query", True)
        self.config["organize_by_query"] = not current
        self.save_config()
        
        status = "启用" if self.config["organize_by_query"] else "禁用"
        print(f"✅ 已{status}按搜索词组织文件夹功能")
    
    def reset_downloaded_papers(self):
        """重置下载记录"""
        self.config["downloaded_papers"] = []
        self.config["last_check"] = None
        self.config["query_last_check"] = {}  # 重置所有查询的检查时间
        self.config["first_run"] = True
        self.save_config()
        print("✅ 已重置下载记录，下次检查时将重新下载论文")
    
    def add_search_query(self, query):
        """添加搜索查询"""
        if query not in self.config["search_queries"]:
            self.config["search_queries"].append(query)
            self.save_config()
            self.logger.info(f"添加搜索查询: {query}")
    
    def remove_search_query(self, query):
        """移除搜索查询"""
        if query in self.config["search_queries"]:
            self.config["search_queries"].remove(query)
            # 同时删除该查询的检查时间记录
            if query in self.config["query_last_check"]:
                del self.config["query_last_check"][query]
            self.save_config()
            self.logger.info(f"移除搜索查询: {query}")
    
    def start_monitoring(self):
        """开始监控"""
        self.logger.info("开始arXiv论文监控...")
        print("🚀 启动arXiv论文监控器...")
        
        # 立即执行一次检查
        self.check_for_new_papers()
        
        # 设置定期检查
        schedule.every(self.config["check_interval_hours"]).hours.do(self.check_for_new_papers)
        
        print(f"⏰ 监控已启动，每 {self.config['check_interval_hours']} 小时检查一次")
        print("💡 按 Ctrl+C 停止监控")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次是否有待执行的任务
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
            print("\n🛑 监控已停止")

def main():
    """主函数"""
    print("="*60)
    print("📚 arXiv论文监控器 v2.1 - 智能文件夹管理版")
    print("="*60)
    
    monitor = ArxivMonitor()
    
    while True:
        print("\n🎯 请选择操作:")
        print("1. 🚀 开始监控")
        print("2. 🔍 手动检查一次")
        print("3. 📋 查看当前搜索主题")
        print("4. ➕ 添加搜索主题")
        print("5. ➖ 删除搜索主题")
        print("6. ⏱️  设置检查间隔")
        print("7. 📊 查看统计信息")
        print("8. 🧪 测试arXiv连接")
        print("9. 🔄 重置下载记录")
        print("A. 📚 查看arXiv分类目录")
        print("B. 📁 切换文件夹组织方式")
        print("0. 🚪 退出")
        
        choice = input("\n请输入选择 (0-9, A-B): ").strip().upper()
        
        if choice == '1':
            monitor.start_monitoring()
        
        elif choice == '2':
            print("🔍 正在检查新论文...")
            monitor.check_for_new_papers()
        
        elif choice == '3':
            print(f"\n📋 当前搜索主题 (共{len(monitor.config['search_queries'])}个):")
            for i, query in enumerate(monitor.config["search_queries"], 1):
                folder_name = monitor.get_folder_name_for_query(query)
                last_check = monitor.config["query_last_check"].get(query, "从未检查")
                if last_check != "从未检查":
                    try:
                        last_check = datetime.fromisoformat(last_check).strftime('%Y-%m-%d %H:%M')
                    except:
                        last_check = "时间格式错误"
                print(f"   {i}. {query:<25} → 📁 {folder_name}")
                print(f"      上次检查: {last_check}")
        
        elif choice == '4':
            print("\n💡 添加搜索主题:")
            print("你可以输入:")
            print("• arXiv分类 (如: cat:cs.AI)")
            print("• 关键词 (如: transformer)")
            print("• 复合查询 (如: cat:cs.AI AND deep learning)")
            print("\n常用示例:")
            
            examples = [
                ("cat:cs.AI", "人工智能"),
                ("cat:cs.LG", "机器学习"),
                ("cat:cs.CV", "计算机视觉"),
                ("cat:cs.CL", "计算语言学/NLP"),
                ("cat:cs.RO", "机器人学"),
                ("cat:stat.ML", "统计机器学习"),
                ("deep learning", "关键词: 深度学习"),
                ("transformer", "关键词: Transformer"),
                ("diffusion model", "关键词: 扩散模型"),
                ("reinforcement learning", "关键词: 强化学习")
            ]
            
            for query, desc in examples:
                print(f"   • {query:<25} ({desc})")
            
            query = input("\n请输入要添加的搜索主题: ").strip()
            if query:
                monitor.add_search_query(query)
                folder_name = monitor.get_folder_name_for_query(query)
                print(f"✅ 已添加搜索主题: {query}")
                print(f"📁 将下载到文件夹: {folder_name}")
        
        elif choice == '5':
            if not monitor.config["search_queries"]:
                print("❌ 没有搜索主题可删除")
                continue
                
            print(f"\n📋 当前搜索主题:")
            for i, query in enumerate(monitor.config["search_queries"], 1):
                print(f"   {i}. {query}")
            
            try:
                index = int(input("\n请输入要删除的主题编号: ")) - 1
                if 0 <= index < len(monitor.config["search_queries"]):
                    removed_query = monitor.config["search_queries"].pop(index)
                    # 删除对应的检查时间记录
                    if removed_query in monitor.config["query_last_check"]:
                        del monitor.config["query_last_check"][removed_query]
                    monitor.save_config()
                    print(f"✅ 已删除搜索主题: {removed_query}")
                else:
                    print("❌ 无效的编号")
            except ValueError:
                print("❌ 请输入有效的数字")
        
        elif choice == '6':
            try:
                current = monitor.config['check_interval_hours']
                hours = int(input(f"请输入检查间隔(小时，当前: {current}): "))
                if hours > 0:
                    monitor.config["check_interval_hours"] = hours
                    monitor.save_config()
                    print(f"✅ 检查间隔已设置为 {hours} 小时")
                else:
                    print("❌ 请输入大于0的数字")
            except ValueError:
                print("❌ 请输入有效的数字")
        
        elif choice == '7':
            print(f"\n📊 统计信息:")
            print(f"   • 搜索主题数量: {len(monitor.config['search_queries'])}")
            print(f"   • 已下载论文数: {len(monitor.config['downloaded_papers'])}")
            print(f"   • 下载路径: {monitor.config['download_path']}")
            print(f"   • 检查间隔: {monitor.config['check_interval_hours']} 小时")
            print(f"   • 首次运行: {'是' if monitor.config.get('first_run', True) else '否'}")
            print(f"   • 文件夹组织: {'启用' if monitor.config.get('organize_by_query', True) else '禁用'}")
            
            # 显示各查询的检查时间
            print(f"\n📅 各查询检查时间:")
            for query in monitor.config['search_queries']:
                last_check = monitor.config["query_last_check"].get(query, "从未检查")
                if last_check != "从未检查":
                    try:
                        last_check = datetime.fromisoformat(last_check).strftime('%Y-%m-%d %H:%M')
                    except:
                        last_check = "时间格式错误"
                print(f"   • {query}: {last_check}")
            
            if monitor.config['last_check']:
                print(f"\n   • 全局上次检查: {monitor.config['last_check'][:19]}")
            else:
                print(f"\n   • 全局上次检查: 从未检查")
            
            # 显示各文件夹统计
            if os.path.exists(monitor.config['download_path']):
                print(f"\n📁 文件夹统计:")
                total_size = 0
                total_files = 0
                
                for root, dirs, files in os.walk(monitor.config['download_path']):
                    pdf_files = [f for f in files if f.endswith('.pdf')]
                    if pdf_files:
                        folder_size = sum(os.path.getsize(os.path.join(root, f)) for f in pdf_files)
                        folder_name = os.path.basename(root) if root != monitor.config['download_path'] else '根目录'
                        print(f"   📂 {folder_name}: {len(pdf_files)} 个文件, {folder_size/1024/1024:.1f} MB")
                        total_size += folder_size
                        total_files += len(pdf_files)
                
                print(f"\n   🎯 总计: {total_files} 个PDF文件, {total_size/1024/1024:.1f} MB")
        
        elif choice == '8':
            monitor.test_arxiv_connection()
        
        elif choice == '9':
            confirm = input("⚠️  确定要重置下载记录吗？这将导致下次检查时重新下载论文 (y/N): ")
            if confirm.lower() in ['y', 'yes']:
                monitor.reset_downloaded_papers()
            else:
                print("❌ 操作已取消")
        
        elif choice == 'A':
            monitor.show_available_categories()
        
        elif choice == 'B':
            current = monitor.config.get("organize_by_query", True)
            print(f"\n📁 当前文件夹组织方式: {'按搜索词分文件夹' if current else '所有文件在同一文件夹'}")
            print("是否要切换组织方式？")
            print("• 启用: 每个搜索词的论文下载到对应的文件夹")
            print("• 禁用: 所有论文下载到同一个文件夹")
            
            confirm = input("确定要切换吗？(y/N): ")
            if confirm.lower() in ['y', 'yes']:
                monitor.toggle_organize_by_query()
            else:
                print("❌ 操作已取消")
        
        elif choice == '0':
            print("👋 再见!")
            break
        
        else:
            print("❌ 无效的选择，请重新输入")

if __name__ == "__main__":
    main()