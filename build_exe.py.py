# package.py
import os
import shutil
import subprocess
import sys
import json

def install_package(package_name):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
        return True
    except subprocess.CalledProcessError:
        return False

def check_pyinstaller():
    """检查并安装PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("❌ PyInstaller 未安装，正在安装...")
        if install_package('pyinstaller'):
            print("✅ PyInstaller 安装成功")
            return True
        else:
            print("❌ PyInstaller 安装失败")
            return False

def create_exe():
    """创建exe文件"""
    print("🚀 开始打包arXiv论文监控器...")
    
    # 检查主程序文件是否存在
    if not os.path.exists('main.py'):
        print("❌ 找不到主程序文件 arxiv_monitor.py")
        print("请确保在正确的目录下运行此脚本")
        return False
    
    # 确保依赖包已安装
    required_packages = [
        'requests', 'schedule', 'plyer', 'pyinstaller'
    ]
    
    print("📦 检查依赖包...")
    for package in required_packages:
        try:
            if package == 'pyinstaller':
                if not check_pyinstaller():
                    return False
            else:
                __import__(package)
                print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装，正在安装...")
            if not install_package(package):
                print(f"❌ {package} 安装失败")
                return False
            print(f"✅ {package} 安装成功")
    
    # 清理旧的构建文件
    print("🧹 清理旧文件...")
    for dir_name in ['dist', 'build']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已删除 {dir_name}")
    
    for file_name in ['ArxivMonitor.spec']:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"已删除 {file_name}")
    
    # 使用Python模块方式调用PyInstaller
    print("🔨 正在编译...")
    try:
        import PyInstaller.__main__
        
        # PyInstaller 参数
        args = [
            '--name=ArxivMonitor',
            '--onefile',
            '--console',  # 保留控制台窗口
            '--clean',
            '--noconfirm',
            'main.py'
        ]
        
        # 添加图标（如果存在）
        if os.path.exists('icon.ico'):
            args.insert(-1, '--icon=icon.ico')
        
        print(f"PyInstaller 参数: {' '.join(args)}")
        
        # 运行PyInstaller
        PyInstaller.__main__.run(args)
        
        print("✅ 编译成功！")
        
        # 检查输出文件
        exe_path = 'dist/ArxivMonitor.exe'
        if os.path.exists(exe_path):
            print(f"📁 exe文件位置: {os.path.abspath(exe_path)}")
            print(f"📏 文件大小: {os.path.getsize(exe_path) / 1024 / 1024:.1f} MB")
            
            # 创建发布目录
            create_release_package(exe_path)
            return True
        else:
            print("❌ 没有找到生成的exe文件")
            return False
            
    except Exception as e:
        print(f"❌ 编译失败: {e}")
        return False

def create_release_package(exe_path):
    """创建发布包"""
    print("📦 创建发布包...")
    
    release_dir = 'release'
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # 复制exe文件
    shutil.copy(exe_path, release_dir)
    print("✅ 已复制exe文件")
    
    # 创建配置文件模板
    config_template = {
        "search_queries": [
            "cat:cs.AI",
            "cat:cs.LG", 
            "cat:cs.CV"
        ],
        "max_results": 10,
        "download_path": "./arxiv_papers",
        "check_interval_hours": 6,
        "last_check": None,
        "downloaded_papers": [],
        "first_run": True,
        "organize_by_query": True
    }
    
    config_path = os.path.join(release_dir, 'arxiv_config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_template, f, indent=2, ensure_ascii=False)
    print("✅ 已创建配置文件模板")
    
    # 创建使用说明
    readme_content = """# arXiv论文监控器 使用说明

## 快速开始
1. 双击 ArxivMonitor.exe 运行程序
2. 首次运行会自动创建配置文件
3. 选择相应选项进行操作

## 主要功能
- 🚀 自动监控arXiv新论文
- 📁 按搜索词自动分类下载
- 🔍 支持类别和关键词搜索
- ⏰ 定时检查更新
- 📊 统计信息查看

## 搜索示例
- cat:cs.AI (人工智能类别)
- cat:cs.LG (机器学习类别)
- cat:cs.CV (计算机视觉类别)
- deep learning (关键词搜索)
- transformer (关键词搜索)

## 文件说明
- ArxivMonitor.exe: 主程序
- arxiv_config.json: 配置文件
- arxiv_monitor.log: 运行日志（运行后生成）
- arxiv_papers/: 论文下载目录（运行后生成）

## 注意事项
- 首次运行需要联网下载论文
- 确保有足够的磁盘空间存储PDF文件
- 程序可能被防火墙拦截，请允许网络访问
- 如果遇到权限问题，请以管理员身份运行

## 系统要求
- Windows 7/10/11
- 网络连接
- 至少100MB可用磁盘空间

## 版本信息
版本: v2.1
更新时间: 2025-07-18
作者: Claude & User

## 常见问题
Q: 程序无法启动？
A: 请检查是否被杀毒软件拦截，添加到信任列表

Q: 下载速度慢？
A: 这取决于网络状况和arXiv服务器响应速度

Q: 如何修改搜索主题？
A: 运行程序后选择选项4添加，或直接编辑arxiv_config.json文件

Q: 如何查看下载的论文？
A: 默认下载到当前目录下的arxiv_papers文件夹中
"""
    
    readme_path = os.path.join(release_dir, 'README.txt')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✅ 已创建使用说明")
    
    # 创建批处理启动文件
    bat_content = """@echo off
chcp 65001 >nul
title arXiv论文监控器
echo 正在启动arXiv论文监控器...
ArxivMonitor.exe
pause
"""
    
    bat_path = os.path.join(release_dir, '启动程序.bat')
    with open(bat_path, 'w', encoding='gbk') as f:
        f.write(bat_content)
    print("✅ 已创建批处理启动文件")
    
    print(f"📦 发布包已创建: {os.path.abspath(release_dir)}")
    
    # 显示发布包内容
    print("\n📁 发布包内容:")
    for item in os.listdir(release_dir):
        item_path = os.path.join(release_dir, item)
        if os.path.isfile(item_path):
            size = os.path.getsize(item_path) / 1024
            print(f"   📄 {item} ({size:.1f} KB)")
    
    print("\n🎉 打包完成！")
    print(f"📍 发布目录: {os.path.abspath(release_dir)}")

def main():
    """主函数"""
    print("="*60)
    print("📚 arXiv论文监控器 打包工具")
    print("="*60)
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"🐍 Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return
    
    # 检查当前目录
    print(f"📂 当前目录: {os.getcwd()}")
    
    # 开始打包
    if create_exe():
        print("\n🎊 打包成功！可以分发 release 文件夹中的内容")
    else:
        print("\n💥 打包失败！请检查错误信息")

if __name__ == "__main__":
    main()