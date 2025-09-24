import os
import re
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
from tkinter.scrolledtext import ScrolledText
from openai import OpenAI
import os
import ctypes

class NovelChapterNamer:
    def __init__(self, root):
        # 启用高DPI支持
        if os.name == 'nt':  # 检查是否为Windows系统
            try:
                # 设置进程DPI感知，解决Windows高DPI屏幕上的模糊问题
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
                # 获取系统DPI缩放因子
                dpi = ctypes.windll.user32.GetDpiForSystem()
                scale_factor = dpi / 96  # 96是标准DPI
                # 设置应用程序缩放因子
                root.tk.call('tk', 'scaling', scale_factor)
            except Exception as e:
                # 如果设置失败，继续使用默认设置
                pass
                
        self.root = root
        self.root.title("小说章节名称生成器")
        self.root.geometry("1200x1000")  # 进一步增大窗口初始尺寸以改善比例协调性
        self.root.minsize(1100, 900)  # 设置最小窗口尺寸
        
        # 设置中文字体（缩小一号字体）
        self.font = ("SimHei", 14)
        
        # 创建自定义样式
        self.style = ttk.Style()
        # 设置Treeview字体样式和行间距（增加rowheight值来扩大行间距）
        self.style.configure("LargeFont.Treeview", font=self.font, rowheight=30)
        self.style.configure("LargeFont.Treeview.Heading", font=self.font)
        # 设置按钮样式（增加宽度以显示完整的中文文本）
        self.style.configure("LargeFont.TButton", font=self.font, padding=6, width=12)
        
        # 数据存储
        self.file_path = ""
        self.file_content = ""
        self.chapters = []
        self.silicon_api_key = ""
        
        # 默认API密钥（可选），仅用于方便使用，注意安全风险
        self.DEFAULT_API_KEY = "sk-ruekitazxvazeyghqobhgkcqsyefvmumtbwifseclhyhylny"  # 在这里填入您的API密钥
        
        # 初始化OpenAI客户端，连接到硅基流动API
        self.client = None
        
        # 默认使用的模型
        self.default_model = "deepseek-ai/DeepSeek-V2.5"
        
        # 创建自定义样式
        self.style = ttk.Style()
        self.style.configure("LargeFont.TButton", font=self.font)
        self.style.configure("LargeFont.TLabelframe.Label", font=self.font)
        
        # 初始化token计数器
        self.total_tokens_used = 0
        self.prompt_tokens_used = 0
        self.completion_tokens_used = 0
        self.total_chapters_processed = 0
        
        # 创建界面
        self._create_widgets()
        
        # 尝试加载配置
        self._load_config()
    
    def _create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部按钮区域 - 使用grid布局优化
        top_frame = ttk.Frame(main_frame, padding="5")
        top_frame.pack(fill=tk.X)
        
        # 创建一个包含所有按钮的内部框架，以便居中对齐
        buttons_container = ttk.Frame(top_frame)
        buttons_container.pack(anchor=tk.CENTER, fill=tk.X)
        
        # 使用grid布局排列按钮，增加统一的内边距
        ttk.Button(buttons_container, text="打开文件", command=self.open_file, style="LargeFont.TButton").grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(buttons_container, text="识别章节", command=self.identify_chapters, style="LargeFont.TButton").grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(buttons_container, text="生成章节名称", command=self.generate_chapter_names, style="LargeFont.TButton").grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(buttons_container, text="保存文件", command=self.save_file, style="LargeFont.TButton").grid(row=0, column=3, padx=10, pady=5)
        
        # 章节管理按钮区域 - 使用grid布局优化
        manage_frame = ttk.Frame(main_frame, padding="5")
        manage_frame.pack(fill=tk.X)
        
        # 为管理按钮创建内部容器
        manage_buttons_container = ttk.Frame(manage_frame)
        manage_buttons_container.pack(anchor=tk.CENTER, fill=tk.X)
        
        ttk.Button(manage_buttons_container, text="删除选中章节", command=self.delete_selected_chapter, style="LargeFont.TButton").grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(manage_buttons_container, text="编辑章节内容", command=self.edit_chapter_content, style="LargeFont.TButton").grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(manage_buttons_container, text="刷新章节序号", command=self.refresh_chapter_indices, style="LargeFont.TButton").grid(row=0, column=2, padx=10, pady=5)
        
        # API Key 设置区域
        api_frame = ttk.LabelFrame(main_frame, text="硅基流动 API 设置", padding="10", style="LargeFont.TLabelframe")
        api_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(api_frame, text="API Key:", font=self.font).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.api_key_entry = ttk.Entry(api_frame, width=50, font=self.font)
        self.api_key_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        ttk.Button(api_frame, text="保存设置", command=self.save_config, style="LargeFont.TButton").grid(row=0, column=2, padx=5)
        
        # 章节正则表达式设置
        regex_frame = ttk.LabelFrame(main_frame, text="章节识别正则表达式", padding="10", style="LargeFont.TLabelframe")
        regex_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(regex_frame, text="正则表达式:", font=self.font).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.regex_entry = ttk.Entry(regex_frame, width=60, font=self.font)
        self.regex_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        # 使用用户提供的更全面的正则表达式
        default_regex = r"^(?:\s*[第卷][0123456789一二三四五六七八九十零〇百千两]*[章回部节集卷].*|\s*Chapter\s*[0123456789]*|\s*[0123456789１２３４５６]|\s*(简介|序言|序[1-9]|序曲|简介|后记|尾声)|\s*(前言|自序|附录))"
        self.regex_entry.insert(0, default_regex)
        
        # 章节名称字数限制设置
        limit_frame = ttk.LabelFrame(main_frame, text="章节名称字数限制", padding="10", style="LargeFont.TLabelframe")
        limit_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(limit_frame, text="最大字数:", font=self.font).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_chars_var = tk.StringVar(value="20")  # 默认20字
        self.max_chars_entry = ttk.Entry(limit_frame, width=10, textvariable=self.max_chars_var, font=self.font)
        self.max_chars_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        ttk.Label(limit_frame, text="字", font=self.font).grid(row=0, column=2, sticky=tk.W, pady=2)
        
        # 章节列表区域
        chapters_frame = ttk.LabelFrame(main_frame, text="章节列表", padding="10", style="LargeFont.TLabelframe")
        chapters_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建Treeview来显示章节列表
        columns = ("index", "original", "new_title")
        self.chapter_tree = ttk.Treeview(chapters_frame, columns=columns, show="headings", style="LargeFont.Treeview")
        
        # 设置列标题和宽度
        self.chapter_tree.heading("index", text="序号")
        self.chapter_tree.heading("original", text="原始章节名")
        self.chapter_tree.heading("new_title", text="新章节名")
        
        self.chapter_tree.column("index", width=80, anchor=tk.CENTER)  # 进一步增加列宽以适应更大字体
        self.chapter_tree.column("original", width=300, anchor=tk.W)
        self.chapter_tree.column("new_title", width=600, anchor=tk.W)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(chapters_frame, orient=tk.VERTICAL, command=self.chapter_tree.yview)
        self.chapter_tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chapter_tree.pack(fill=tk.BOTH, expand=True)
        
        # 绑定双击事件以编辑章节名
        self.chapter_tree.bind("<Double-1>", self.on_double_click)
        
        # 状态信息区域
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, font=self.font)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_file(self):
        """打开文件并读取内容"""
        file_types = [("文本文件", "*.txt"), ("所有文件", "*.*")]
        self.file_path = filedialog.askopenfilename(title="选择小说文件", filetypes=file_types)
        
        if self.file_path:
            try:
                # 尝试不同的编码读取文件
                encodings = ["utf-8", "gbk", "gb2312", "utf-16"]
                for encoding in encodings:
                    try:
                        with open(self.file_path, "r", encoding=encoding) as f:
                            self.file_content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                self.status_var.set(f"已打开文件: {os.path.basename(self.file_path)}")
                messagebox.showinfo("成功", f"文件已成功打开: {os.path.basename(self.file_path)}")
                
                # 自动识别章节
                self.identify_chapters()
                
            except Exception as e:
                messagebox.showerror("错误", f"打开文件时出错: {str(e)}")
                self.status_var.set(f"打开文件失败: {str(e)}")
    
    def identify_chapters(self):
        """使用正则表达式识别章节"""
        if not self.file_content:
            messagebox.showwarning("警告", "请先打开一个文件")
            return
        
        try:
            # 获取正则表达式
            regex_pattern = self.regex_entry.get()
            if not regex_pattern:
                messagebox.showwarning("警告", "请输入章节识别正则表达式")
                return
            
            # 清空现有章节
            for item in self.chapter_tree.get_children():
                self.chapter_tree.delete(item)
            
            self.chapters = []
            
            # 使用正则表达式查找章节
            pattern = re.compile(regex_pattern, re.MULTILINE)
            matches = pattern.finditer(self.file_content)
            
            # 处理匹配结果
            last_end = 0
            matches_list = list(matches)  # 预先转换为列表以便多次访问
            
            for i, match in enumerate(matches_list):
                start, end = match.span()
                chapter_name = match.group().strip()
                
                # 提取章节内容
                if i < len(matches_list) - 1:
                    next_match = matches_list[i+1]
                    content = self.file_content[end:next_match.start()]
                else:
                    content = self.file_content[end:]
                
                self.chapters.append({
                    "index": i+1,
                    "original": chapter_name,
                    "content": content,
                    "start_pos": start,
                    "end_pos": end,
                    "new_title": ""
                })
                
                # 添加到Treeview
                self.chapter_tree.insert("", tk.END, values=(i+1, chapter_name, ""))
                
            self.status_var.set(f"已识别 {len(self.chapters)} 个章节")
            messagebox.showinfo("成功", f"已识别 {len(self.chapters)} 个章节")
            
        except Exception as e:
            messagebox.showerror("错误", f"识别章节时出错: {str(e)}")
            self.status_var.set(f"识别章节失败: {str(e)}")
    
    def on_double_click(self, event):
        """双击编辑章节名"""
        region = self.chapter_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.chapter_tree.identify_column(event.x)
            item = self.chapter_tree.identify_row(event.y)
            
            if column == "#3":  # 新章节名列
                self.edit_chapter_title(item)
            elif column == "#2":  # 原始章节名列
                self.edit_original_chapter_name(item)
    
    def edit_chapter_title(self, item):
        """编辑章节标题"""
        x, y, width, height = self.chapter_tree.bbox(item, "#3")
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑章节名称")
        edit_window.geometry(f"400x120+{self.root.winfo_rootx()+x}+{self.root.winfo_rooty()+y}")
        edit_window.resizable(False, False)
        
        # 获取当前值
        current_value = self.chapter_tree.item(item, "values")[2]
        
        # 创建输入框
        ttk.Label(edit_window, text="章节名称:", font=self.font).pack(pady=10, padx=10, anchor=tk.W)
        entry = ttk.Entry(edit_window, width=40, font=self.font)
        entry.pack(pady=5, padx=10, fill=tk.X)
        entry.insert(0, current_value)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        # 保存按钮
        def save_edit():
            new_value = entry.get()
            
            # 检查字数限制
            try:
                max_chars = int(self.max_chars_var.get())
                if len(new_value) > max_chars:
                    messagebox.showwarning("警告", f"章节名称超过{max_chars}字限制")
                    return
            except ValueError:
                messagebox.showwarning("警告", "请输入有效的字数限制")
                return
            
            values = list(self.chapter_tree.item(item, "values"))
            values[2] = new_value
            self.chapter_tree.item(item, values=values)
            
            # 更新数据
            index = int(values[0]) - 1
            if 0 <= index < len(self.chapters):
                self.chapters[index]["new_title"] = new_value
            
            edit_window.destroy()
        
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(pady=10, fill=tk.X, padx=10)
        ttk.Button(button_frame, text="保存", command=save_edit).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT)
        
        # 按Enter保存，按Escape取消
        edit_window.bind("<Return>", lambda e: save_edit())
        edit_window.bind("<Escape>", lambda e: edit_window.destroy())
        
    def edit_original_chapter_name(self, item):
        """编辑原始章节名"""
        x, y, width, height = self.chapter_tree.bbox(item, "#2")
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑原始章节名")
        edit_window.geometry(f"400x120+{self.root.winfo_rootx()+x}+{self.root.winfo_rooty()+y}")
        edit_window.resizable(False, False)
        
        # 获取当前值
        current_value = self.chapter_tree.item(item, "values")[1]
        
        # 创建输入框
        ttk.Label(edit_window, text="原始章节名:", font=self.font).pack(pady=10, padx=10, anchor=tk.W)
        entry = ttk.Entry(edit_window, width=40, font=self.font)
        entry.pack(pady=5, padx=10, fill=tk.X)
        entry.insert(0, current_value)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        # 保存按钮
        def save_edit():
            new_value = entry.get().strip()
            if not new_value:
                messagebox.showwarning("警告", "章节名不能为空")
                return
            
            values = list(self.chapter_tree.item(item, "values"))
            values[1] = new_value
            self.chapter_tree.item(item, values=values)
            
            # 更新数据
            index = int(values[0]) - 1
            if 0 <= index < len(self.chapters):
                self.chapters[index]["original"] = new_value
            
            edit_window.destroy()
        
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(pady=10, fill=tk.X, padx=10)
        ttk.Button(button_frame, text="保存", command=save_edit).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT)
        
        # 按Enter保存，按Escape取消
        edit_window.bind("<Return>", lambda e: save_edit())
        edit_window.bind("<Escape>", lambda e: edit_window.destroy())
    
    def generate_chapter_names(self):
        """使用硅基流动大模型生成章节名称"""
        if not self.chapters:
            messagebox.showwarning("警告", "请先识别章节")
            return
        
        # 获取API Key（如果用户已输入）
        user_api_key = self.api_key_entry.get().strip()
        if user_api_key:
            self.silicon_api_key = user_api_key
            # 保存API Key
            self.save_config()
        
        # 重置token计数器
        self.total_tokens_used = 0
        self.prompt_tokens_used = 0
        self.completion_tokens_used = 0
        self.total_chapters_processed = 0
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key=self.silicon_api_key if self.silicon_api_key else self.DEFAULT_API_KEY
        )
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("生成章节名称")
        progress_window.geometry("400x120")
        progress_window.resizable(False, False)
        
        ttk.Label(progress_window, text="正在生成章节名称，请稍候...", font=self.font).pack(pady=20)
        progress_bar = ttk.Progressbar(progress_window, orient=tk.HORIZONTAL, length=300, mode='determinate')
        progress_bar.pack(pady=10)
        
        progress_window.update()
        
        try:
            # 确保只处理当前章节列表中的章节（已删除的不再处理）
            total_chapters = len(self.chapters)
            
            for i, chapter in enumerate(self.chapters):
                # 更新进度
                progress = (i + 1) / total_chapters * 100
                progress_bar['value'] = progress
                progress_window.update()
                
                # 生成章节名称，添加重试和延迟机制
                new_title = self._call_silicon_api_with_retry(chapter["content"])
                
                if new_title:
                    # 本地再次去除所有引号，包括中文双引号和书名号
                    clean_title = re.sub(r'["\']|[“”「」]|《|》', '', new_title)
                    chapter["new_title"] = clean_title
                    # 更新Treeview
                    for item in self.chapter_tree.get_children():
                        values = self.chapter_tree.item(item, "values")
                        if values[0] == str(chapter["index"]):
                            new_values = list(values)
                            new_values[2] = new_title
                            self.chapter_tree.item(item, values=new_values)
                            break
                
                # 在每次API调用后添加短暂延迟，避免触发速率限制
                import time
                time.sleep(1)  # 1秒延迟
                self.root.update()
            
            progress_window.destroy()
            
            # 显示token使用情况
            token_info = f"章节名称生成完成！\n\n" \
                        f"处理章节数: {self.total_chapters_processed}\n" \
                        f"总Token使用量: {self.total_tokens_used}\n" \
                        f"提示Token数: {self.prompt_tokens_used}\n" \
                        f"完成Token数: {self.completion_tokens_used}"
            
            self.status_var.set("章节名称生成完成")
            messagebox.showinfo("成功", token_info)
            
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("错误", f"生成章节名称时出错: {str(e)}")
            self.status_var.set(f"生成章节名称失败: {str(e)}")
    
    def _call_silicon_api(self, content):
        """调用硅基流动API生成章节名称"""
        try:
            # 确保客户端已初始化
            if self.client is None:
                api_key = self.silicon_api_key if self.silicon_api_key else self.DEFAULT_API_KEY
                self.client = OpenAI(
                    base_url="https://api.siliconflow.cn/v1",
                    api_key=api_key
                )
            
            # 构建提示词，包含用户设置的字数限制
            try:
                max_chars = int(self.max_chars_var.get())
            except ValueError:
                max_chars = 20  # 默认20字
                
            prompt = f"以下是小说的一个章节内容，请为这个章节生成一个合适的标题。标题应简洁明了，能够概括章节的主要内容，不要超过{max_chars}个字。\n\n章节内容：{content[:1000]}...\n\n标题："
            
            # 使用OpenAI客户端调用API
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "你是一个小说编辑助手，擅长为小说章节生成简洁而有吸引力的标题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # 更新token计数
            if hasattr(response, 'usage'):
                self.total_tokens_used += response.usage.total_tokens
                self.prompt_tokens_used += response.usage.prompt_tokens
                self.completion_tokens_used += response.usage.completion_tokens
            
            # 处理响应
            title = response.choices[0].message.content.strip()
            # 去除所有引号，包括中文双引号和书名号
            title = re.sub(r'["\']|[“”「」]|《|》', '', title)
            
            # 检查字数限制，如果超过则截断
            try:
                max_chars = int(self.max_chars_var.get())
                if len(title) > max_chars:
                    title = title[:max_chars] + '...'  # 超过限制截断并添加省略号
            except ValueError:
                pass  # 如果设置无效则忽略
            
            # 更新处理的章节数
            self.total_chapters_processed += 1
            
            return title
            
        except Exception as e:
            print(f"API调用错误: {str(e)}")
            # 向上抛出异常，让调用者处理重试逻辑
            raise
    
    def _call_silicon_api_with_retry(self, content, max_retries=3, initial_delay=2):
        """带重试机制的API调用，用于处理速率限制错误"""
        retry_count = 0
        delay = initial_delay
        
        while retry_count < max_retries:
            try:
                return self._call_silicon_api(content)
            except Exception as e:
                # 检查是否是速率限制错误
                error_message = str(e)
                if "429" in error_message and ("rate limiting" in error_message or "TPM limit" in error_message):
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"达到最大重试次数，无法完成API调用: {error_message}")
                        self.status_var.set(f"API调用受限制，已达到最大重试次数")
                        return ""
                    
                    # 显示重试信息
                    print(f"API速率限制，{delay}秒后重试... (第{retry_count}/{max_retries}次)")
                    self.status_var.set(f"API调用受限制，{delay}秒后重试...")
                    
                    # 等待延迟时间
                    import time
                    for _ in range(delay):
                        time.sleep(1)
                        self.root.update()
                    
                    # 指数退避
                    delay *= 2  # 每次重试延迟翻倍
                else:
                    # 其他错误，直接返回空字符串
                    print(f"API调用非速率限制错误: {error_message}")
                    return ""
    
    def save_file(self):
        """保存新的章节文件"""
        if not self.file_path or not self.chapters:
            messagebox.showwarning("警告", "请先打开文件并识别章节")
            return
            
        # 获取保存路径
        file_name = os.path.basename(self.file_path)
        base_name, ext = os.path.splitext(file_name)
        new_file_name = f"{base_name}【目录】{ext}"
        
        save_path = filedialog.asksaveasfilename(
            title="保存文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=new_file_name
        )
        
        if save_path:
            try:
                # 创建新的内容
                new_content = ""
                last_pos = 0
                
                for chapter in sorted(self.chapters, key=lambda x: x["start_pos"]):
                    # 添加章节前的内容
                    new_content += self.file_content[last_pos:chapter["start_pos"]]
                    
                    # 添加带新标题的章节，按照顺序重新编号
                    if chapter["new_title"]:
                        # 生成新的章节标记，如第1章、第2章等
                        new_chapter_mark = f"第{chapter['index']}章"
                        # 确保标题中没有引号，包括中文双引号和书名号
                        clean_title = re.sub(r'["\']|[“”「」]|《|》', '', chapter['new_title'])
                        new_content += f"{new_chapter_mark} {clean_title}\n"
                    else:
                        new_content += chapter['original'] + "\n"
                    
                    # 添加章节内容
                    new_content += chapter['content']
                    
                    last_pos = chapter["end_pos"] + len(chapter['content'])
                
                # 添加最后一个章节之后的内容
                new_content += self.file_content[last_pos:]
                
                # 保存文件
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                self.status_var.set(f"文件已保存: {os.path.basename(save_path)}")
                messagebox.showinfo("成功", f"文件已成功保存到:\n{save_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")
                self.status_var.set(f"保存文件失败: {str(e)}")
            
    def delete_selected_chapter(self):
        """删除选中的章节"""
        selected_items = self.chapter_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的章节")
            return
        
        # 确认删除
        if messagebox.askyesno("确认", "确定要删除选中的章节吗？"):
            # 按照章节索引从大到小删除，避免索引混乱
            indices_to_delete = []
            for item in selected_items:
                values = self.chapter_tree.item(item, "values")
                index = int(values[0]) - 1  # 转换为0-based索引
                indices_to_delete.append(index)
            
            # 从大到小排序，确保删除顺序正确
            indices_to_delete.sort(reverse=True)
            
            for index in indices_to_delete:
                if 0 <= index < len(self.chapters):
                    del self.chapters[index]
                
                # 从Treeview中删除对应项
                for item in self.chapter_tree.get_children():
                    values = self.chapter_tree.item(item, "values")
                    if int(values[0]) - 1 == index:
                        self.chapter_tree.delete(item)
                        break
            
            # 刷新章节序号
            self.refresh_chapter_indices()
            
            self.status_var.set(f"已删除 {len(selected_items)} 个章节")
            messagebox.showinfo("成功", f"已删除 {len(selected_items)} 个章节")
            
    def refresh_chapter_indices(self):
        """刷新章节序号"""
        # 清空Treeview并重新添加章节
        for item in self.chapter_tree.get_children():
            self.chapter_tree.delete(item)
        
        # 重新添加所有章节并更新索引
        for i, chapter in enumerate(self.chapters):
            chapter["index"] = i + 1
            self.chapter_tree.insert("", tk.END, values=(i+1, chapter["original"], chapter["new_title"]))
            
        self.status_var.set(f"章节列表已更新，共 {len(self.chapters)} 个章节")
        
    def edit_chapter_content(self):
        """编辑章节内容"""
        selected_items = self.chapter_tree.selection()
        if not selected_items or len(selected_items) > 1:
            messagebox.showwarning("警告", "请选择一个章节进行编辑")
            return
        
        item = selected_items[0]
        # 获取章节索引
        values = self.chapter_tree.item(item, "values")
        index = int(values[0]) - 1
        
        if 0 <= index < len(self.chapters):
            chapter = self.chapters[index]
            
            # 创建编辑窗口
            edit_window = tk.Toplevel(self.root)
            edit_window.title("编辑章节内容")
            edit_window.geometry("600x400")
            
            # 创建文本框
            ttk.Label(edit_window, text=f"章节 {chapter['original']} 的内容:", font=self.font).pack(pady=10, padx=10, anchor=tk.W)
            
            text_frame = ttk.Frame(edit_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=self.font)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.config(yscrollcommand=scrollbar.set)
            
            # 填充当前内容
            text_widget.insert(tk.END, chapter["content"])
            
            # 保存按钮
            def save_content():
                new_content = text_widget.get(1.0, tk.END).strip()
                
                # 更新数据
                self.chapters[index]["content"] = new_content
                
                edit_window.destroy()
                messagebox.showinfo("成功", "章节内容已更新")
            
            button_frame = ttk.Frame(edit_window)
            button_frame.pack(pady=10, fill=tk.X, padx=10)
            ttk.Button(button_frame, text="保存", command=save_content).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT)
        
        # 获取保存路径
        file_name = os.path.basename(self.file_path)
        base_name, ext = os.path.splitext(file_name)
        new_file_name = f"{base_name}【目录】{ext}"
        
        save_path = filedialog.asksaveasfilename(
            title="保存文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=new_file_name
        )
        
        if save_path:
            try:
                # 创建新的内容
                new_content = ""
                last_pos = 0
                
                for chapter in sorted(self.chapters, key=lambda x: x["start_pos"]):
                    # 添加章节前的内容
                    new_content += self.file_content[last_pos:chapter["start_pos"]]
                    
                    # 添加带新标题的章节
                    if chapter["new_title"]:
                        new_content += f"{chapter['original']} {chapter['new_title']}\n"
                    else:
                        new_content += chapter['original'] + "\n"
                    
                    # 添加章节内容
                    new_content += chapter['content']
                    
                    last_pos = chapter["end_pos"] + len(chapter['content'])
                
                # 添加最后一个章节之后的内容
                new_content += self.file_content[last_pos:]
                
                # 保存文件
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                self.status_var.set(f"文件已保存: {os.path.basename(save_path)}")
                messagebox.showinfo("成功", f"文件已成功保存到:\n{save_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")
                self.status_var.set(f"保存文件失败: {str(e)}")
    
    def _load_config(self):
        """加载配置"""
        config_file = "config.json"
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "api_key" in config:
                        self.silicon_api_key = config["api_key"]
                        self.api_key_entry.insert(0, self.silicon_api_key)
                    if "regex" in config:
                        self.regex_entry.delete(0, tk.END)
                        self.regex_entry.insert(0, config["regex"])
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        config_file = "config.json"
        try:
            config = {
                "api_key": self.api_key_entry.get().strip(),
                "regex": self.regex_entry.get().strip()
            }
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.status_var.set("配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时出错: {str(e)}")
            self.status_var.set(f"保存配置失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NovelChapterNamer(root)
    root.mainloop()