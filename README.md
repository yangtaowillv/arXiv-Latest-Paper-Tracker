# 📚 arXiv Latest Paper Tracker  v1.0

一个智能的arXiv论文监控和下载工具，支持按搜索词自动分类文件夹管理，让您轻松跟踪最新的学术论文！

## ✨ 主要功能

- 🔍 **智能搜索** - 支持arXiv官方分类、关键词和复合查询  
- 📁 **自动分类** - 按搜索词自动创建文件夹组织论文  
- ⏰ **定时监控** - 自定义时间间隔自动检查新论文  
- 📥 **批量下载** - 自动下载新发布的论文PDF  
- 🔔 **桌面通知** - 实时通知新论文下载状态  
- 📊 **统计分析** - 详细的下载统计和文件夹管理
- 🎯 **精准过滤** - 避免重复下载，按时间过滤新论文

## 🚀 快速开始  

### 安装依赖  

选择操作模式

🚀 开始监控 - 启动定时监控模式  
🔍 手动检查 - 立即检查一次新论文  
📋 管理搜索 - 添加/删除搜索主题  

📖 使用指南  
搜索主题配置  
支持多种搜索方式：  

📂 arXiv分类搜索  
"cat:cs.AI"      # 人工智能  
"cat:cs.LG"      # 机器学习  
"cat:cs.CV"      # 计算机视觉  
"cat:cs.CL"      # 自然语言处理

🔤 关键词搜索  
"transformer"           # Transformer模型  
"deep learning"         # 深度学习  
"diffusion model"       # 扩散模型  
"large language model"  # 大语言模型  
"cat:cs.AI AND transformer"           # AI分类中的Transformer论文  
"deep learning AND computer vision"   # 深度学习与计算机视觉交叉  

文件夹组织结构  
启用按搜索词组织时，会自动创建如下结构：  
arxiv_papers/  
├── 01_人工智能_AI/           # cat:cs.AI  
├── 03_计算机视觉_CV/         # cat:cs.CV    
├── 关键词_Transformer/       # transformer  
├── 关键词_深度学习_DeepLearning/ # deep learning  
└── ...  


⚙️ 配置说明  
配置项	说明	默认值  
search_queries	搜索主题列表	["cat:cs.CV", "llava", "llava-med"]  
max_results	每次搜索最大结果数	5  
download_path	下载目录	"./arxiv_papers"  
check_interval_hours	检查间隔(小时)	6  
organize_by_query	是否按搜索词组织文件夹	true  
自定义配置  
可以通过编辑 config.py 文件来自定义：  
# 添加自定义查询映射  
query_mapping = {
    "your_query": "自定义文件夹名称",
    # ...
}  

# 修改默认配置  
default_config = {
    "search_queries": ["your_favorite_topics"],
    "max_results": 10,
    # ...
}  
📊 功能特性  
🎯 智能过滤  
时间过滤 - 只下载指定时间后的新论文  
去重机制 - 自动避免重复下载相同论文  
分查询跟踪 - 每个搜索词独立跟踪检查时间  
📁 文件管理  
自动命名 - 论文ID + 安全标题格式  
分类存储 - 按搜索主题自动分文件夹  
中文友好 - 支持中文文件夹名称  
🔔 通知系统  
实时通知 - 新论文下载完成桌面通知  
详细日志 - 完整的操作日志记录  
进度显示 - 实时显示下载进度  

📋 arXiv分类速查  

🖥️ 计算机科学  
cs.AI - 人工智能  
cs.LG - 机器学习  
cs.CV - 计算机视觉  
cs.CL - 计算语言学/NLP  
cs.RO - 机器人学  
cs.CR - 密码学与安全  
cs.IR - 信息检索  

📊 统计学  
stat.ML - 统计机器学习  
stat.AP - 应用统计  
stat.CO - 计算统计  
🧮 数学  

math.OC - 优化与控制  
math.PR - 概率论  
math.ST - 统计理论  
💡 使用 查看arXiv分类目录 功能查看完整分类列表  


🔧 高级用法  
定制搜索策略  
# 复杂查询示例  
search_queries = [
    "cat:cs.AI AND (transformer OR attention)",
    "cat:cs.CV AND deep learning",
    "au:Bengio AND cat:cs.LG"  # 特定作者
]  
批量管理  
📁 批量添加搜索主题  
🗂️ 一键切换文件夹组织方式  
📊 统计信息导出  

🤝 贡献  
欢迎提交Issue和Pull Request！  

📞 支持  
如果您觉得这个项目有用，请给它一个⭐星标！  

有任何问题或建议，欢迎：  

📧 提交Issue  
💬 参与Discussions  
🐛 报告Bug  

<div align="center">  

🎓 让学术研究更高效 | 📚 让知识获取更简单  

Made with ❤️ for researchers and students  

</div>  