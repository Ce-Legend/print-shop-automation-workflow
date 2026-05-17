"""
主界面UI模块
提供打印系统的图形用户界面
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import logging
import time
from datetime import datetime
from typing import Optional

from print_system import PrintSystem
from ui_printer_config import PrinterConfigDialog


class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        self.root = tk.Tk()
        self.root.title("打印店自动化打印系统")
        self.root.geometry("1000x700")
        
        # 设置窗口图标（如果有的话）
        # self.root.iconbitmap("icon.ico")
        
        # 初始化打印系统
        self.print_system = PrintSystem()
        
        # UI更新标志
        self._ui_update_running = False
        
        # 创建UI
        self._create_ui()
        
        # 设置日志处理器
        self._setup_logging()
        
        # 启动UI更新线程
        self._start_ui_update()
        
        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _create_ui(self):
        """创建用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 顶部控制面板
        self._create_control_panel(main_frame)
        
        # 状态面板
        self._create_status_panel(main_frame)
        
        # 任务和日志面板
        self._create_task_log_panel(main_frame)
        
        # 底部信息栏
        self._create_status_bar(main_frame)
        
    def _create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="系统控制", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 第一行：监控路径
        ttk.Label(control_frame, text="监控路径:").grid(row=0, column=0, sticky=tk.W)
        
        self.monitor_path_var = tk.StringVar(value=self.print_system.config_manager.get_monitor_path())
        self.monitor_path_entry = ttk.Entry(control_frame, textvariable=self.monitor_path_var, width=50)
        self.monitor_path_entry.grid(row=0, column=1, padx=5)
        
        ttk.Button(control_frame, text="浏览", command=self._browse_monitor_path).grid(row=0, column=2)
        
        # 第二行：主要控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="启动系统", command=self._start_system)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(button_frame, text="暂停", command=self._pause_system, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止系统", command=self._stop_system, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(button_frame, text="打印机配置", command=self._open_printer_config).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # 预设配置相关按钮
        ttk.Button(button_frame, text="🎯 预设配置引导", command=self._open_preset_guide).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔍 配置状态检查", command=self._open_config_checker).pack(side=tk.LEFT, padx=5)
        
        # 第三行：选项
        option_frame = ttk.Frame(control_frame)
        option_frame.grid(row=2, column=0, columnspan=3, pady=5)
        
        self.preprocess_var = tk.BooleanVar(value=self.print_system.config_manager.is_preprocessing_enabled())
        ttk.Checkbutton(
            option_frame, 
            text="启用拍立得预处理", 
            variable=self.preprocess_var,
            command=self._toggle_preprocessing
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Label(option_frame, text="等待时间(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.wait_time_var = tk.IntVar(value=self.print_system.config_manager.get_wait_time())
        wait_time_spinbox = ttk.Spinbox(
            option_frame, 
            from_=10, 
            to=300, 
            width=10,
            textvariable=self.wait_time_var,
            command=self._update_wait_time
        )
        wait_time_spinbox.pack(side=tk.LEFT)
        
    def _create_status_panel(self, parent):
        """创建状态面板"""
        status_frame = ttk.LabelFrame(parent, text="系统状态", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建状态网格
        self.status_labels = {}
        
        # 第一行
        ttk.Label(status_frame, text="系统状态:").grid(row=0, column=0, sticky=tk.W)
        self.status_labels['system'] = ttk.Label(status_frame, text="未启动", foreground="gray")
        self.status_labels['system'].grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="监控状态:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.status_labels['monitor'] = ttk.Label(status_frame, text="未监控", foreground="gray")
        self.status_labels['monitor'].grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="语音队列:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        self.status_labels['voice'] = ttk.Label(status_frame, text="0", foreground="green")
        self.status_labels['voice'].grid(row=0, column=5, sticky=tk.W, padx=5)
        
        # 第二行
        ttk.Label(status_frame, text="总任务数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.status_labels['total_tasks'] = ttk.Label(status_frame, text="0")
        self.status_labels['total_tasks'].grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="完成任务:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0))
        self.status_labels['completed'] = ttk.Label(status_frame, text="0", foreground="green")
        self.status_labels['completed'].grid(row=1, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="失败任务:").grid(row=1, column=4, sticky=tk.W, padx=(20, 0))
        self.status_labels['failed'] = ttk.Label(status_frame, text="0", foreground="red")
        self.status_labels['failed'].grid(row=1, column=5, sticky=tk.W, padx=5)
        
        # 第三行：启用的打印机
        ttk.Label(status_frame, text="启用打印机:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.status_labels['printers'] = ttk.Label(status_frame, text="无", wraplength=700)
        self.status_labels['printers'].grid(row=2, column=1, columnspan=5, sticky=tk.W, padx=5)
        
        # 第四行：预设配置状态
        ttk.Label(status_frame, text="预设配置:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.status_labels['preset_config'] = ttk.Label(status_frame, text="检查中...", foreground="orange")
        self.status_labels['preset_config'].grid(row=3, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="高级配置:").grid(row=3, column=2, sticky=tk.W, padx=(20, 0))
        self.status_labels['advanced_config'] = ttk.Label(status_frame, text="检查中...", foreground="orange")
        self.status_labels['advanced_config'].grid(row=3, column=3, sticky=tk.W, padx=5)
        
        # 预设配置快捷按钮
        preset_btn_frame = ttk.Frame(status_frame)
        preset_btn_frame.grid(row=3, column=4, columnspan=2, sticky=tk.W, padx=(20, 0))
        
        ttk.Button(preset_btn_frame, text="🎯", command=self._open_preset_guide, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="🔍", command=self._open_config_checker, width=3).pack(side=tk.LEFT, padx=2)
        
    def _create_task_log_panel(self, parent):
        """创建完整的系统管理标签页面板"""
        # 创建主标签页
        self.main_notebook = ttk.Notebook(parent)
        self.main_notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 1. 文件夹操作日志标签页
        self.folder_log_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.folder_log_frame, text="文件夹操作日志")
        self._create_folder_log_view(self.folder_log_frame)
        
        # 2. 批量打印管理标签页 ⭐ 新增
        self.batch_print_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.batch_print_frame, text="批量打印管理")
        self._create_batch_print_tab(self.batch_print_frame)
        
        # 3. 异常订单日志标签页
        self.exception_log_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.exception_log_frame, text="异常订单日志")
        self._create_exception_log_view(self.exception_log_frame)
        
        # 4. 打印机状态监控日志标签页
        self.printer_status_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.printer_status_frame, text="打印机状态监控日志")
        self._create_printer_status_log_view(self.printer_status_frame)
        
        # 5. 播报日志标签页
        self.voice_log_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.voice_log_frame, text="播报日志")
        self._create_voice_log_view(self.voice_log_frame)
    
    def _create_printer_status_log_view(self, parent):
        """创建打印机状态监控日志视图"""
        # 创建文本框
        self.printer_status_log_text = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.printer_status_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加右键菜单
        status_log_menu = tk.Menu(self.printer_status_log_text, tearoff=0)
        status_log_menu.add_command(label="清空日志", command=self._clear_printer_status_log)
        status_log_menu.add_command(label="保存日志", command=self._save_printer_status_log)
        
        def show_status_log_menu(event):
            status_log_menu.post(event.x_root, event.y_root)
        
        self.printer_status_log_text.bind("<Button-3>", show_status_log_menu)
    
    def _create_folder_system_tab(self, parent):
        """创建文件夹打印系统标签页"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # 控制面板
        control_frame = ttk.LabelFrame(parent, text="文件夹打印系统控制", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 系统控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W)
        
        self.folder_start_btn = ttk.Button(button_frame, text="启动文件夹打印系统", 
                                          command=self._start_folder_system)
        self.folder_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.folder_stop_btn = ttk.Button(button_frame, text="关闭文件夹打印系统", 
                                         command=self._stop_folder_system, state=tk.DISABLED)
        self.folder_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 自动启用打印机开关
        self.auto_enable_var = tk.BooleanVar(value=True)
                # 动态显示当前配置的等待时间
        wait_time = self.print_system.config_manager.get_wait_time()
        self.auto_enable_checkbox = ttk.Checkbutton(button_frame, text=f"自动启用打印机（{wait_time}秒倒计时）", 
                        variable=self.auto_enable_var)
        self.auto_enable_checkbox.pack(side=tk.LEFT, padx=20)
        
        # 创建子标签页
        folder_notebook = ttk.Notebook(parent)
        folder_notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 系统日志（新增）
        system_log_frame = ttk.Frame(folder_notebook)
        folder_notebook.add(system_log_frame, text="系统日志")
        self._create_system_log_view(system_log_frame)
        
        # 文件夹操作日志
        folder_log_frame = ttk.Frame(folder_notebook)
        folder_notebook.add(folder_log_frame, text="文件夹操作日志")
        self._create_folder_log_view(folder_log_frame)
        
        # 异常日志
        exception_log_frame = ttk.Frame(folder_notebook)
        folder_notebook.add(exception_log_frame, text="异常日志")
        self._create_exception_log_view(exception_log_frame)
    
    def _create_system_log_view(self, parent):
        """创建系统日志视图"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 创建日志文本框
        self.main_log_text = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.main_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置标签样式
        self.main_log_text.tag_config('INFO', foreground='black')
        self.main_log_text.tag_config('WARNING', foreground='orange')
        self.main_log_text.tag_config('ERROR', foreground='red')
        self.main_log_text.tag_config('DEBUG', foreground='gray')
        
        # 控制按钮
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(control_frame, text="清空日志", command=self._clear_main_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存日志", command=self._save_main_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="自动滚动", command=self._toggle_auto_scroll).pack(side=tk.LEFT, padx=5)
        
        # 自动滚动开关
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = ttk.Checkbutton(control_frame, text="自动滚动", variable=self.auto_scroll_var)
        self.auto_scroll_check.pack(side=tk.LEFT, padx=5)
        
        # 右键菜单
        main_log_menu = tk.Menu(self.main_log_text, tearoff=0)
        main_log_menu.add_command(label="复制", command=lambda: self._copy_log_selection(self.main_log_text))
        main_log_menu.add_command(label="全选", command=lambda: self.main_log_text.tag_add(tk.SEL, "1.0", tk.END))
        main_log_menu.add_separator()
        main_log_menu.add_command(label="清空", command=self._clear_main_log)
        main_log_menu.add_command(label="保存", command=self._save_main_log)
        
        def show_main_log_menu(event):
            try:
                main_log_menu.tk_popup(event.x_root, event.y_root)
            finally:
                main_log_menu.grab_release()
        
        self.main_log_text.bind("<Button-3>", show_main_log_menu)
    
    def _clear_main_log(self):
        """清空主日志"""
        if hasattr(self, 'main_log_text'):
            self.main_log_text.delete(1.0, tk.END)
    
    def _save_main_log(self):
        """保存主日志"""
        if hasattr(self, 'main_log_text'):
            self._save_text_to_file(self.main_log_text, "系统日志")
    
    def _toggle_auto_scroll(self):
        """切换自动滚动"""
        pass  # 已经有复选框控制
    
    def _copy_log_selection(self, text_widget):
        """复制日志选中内容"""
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.clipboard_clear()
            text_widget.clipboard_append(selected_text)
        except tk.TkError:
            pass  # 没有选中内容
    
    def _create_printer_config_tab(self, parent):
        """创建打印机配置系统标签页"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # 控制面板
        control_frame = ttk.LabelFrame(parent, text="打印机配置管理", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 打印机操作按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Button(button_frame, text="刷新打印机列表", 
                  command=self._refresh_printer_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="批量启用", 
                  command=self._batch_enable_printers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="批量禁用", 
                  command=self._batch_disable_printers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="详细配置", 
                  command=self._open_printer_config).pack(side=tk.LEFT, padx=5)
        
        # 打印机状态表格
        self._create_printer_status_table(parent)
    
    def _create_voice_system_tab(self, parent):
        """创建播报系统标签页"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # 控制面板
        control_frame = ttk.LabelFrame(parent, text="播报系统控制", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 播报控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W)
        
        self.voice_start_btn = ttk.Button(button_frame, text="打开播报系统", 
                                         command=self._start_voice_system)
        self.voice_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.voice_stop_btn = ttk.Button(button_frame, text="关闭播报系统", 
                                        command=self._stop_voice_system, state=tk.DISABLED)
        self.voice_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 测试按钮
        ttk.Button(button_frame, text="测试播报", 
                  command=self._test_voice).pack(side=tk.LEFT, padx=20)
        
        # 播报日志
        voice_log_frame = ttk.Frame(parent)
        voice_log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(voice_log_frame, text="播报日志", font=("Arial", 12, "bold")).pack(pady=5)
        self._create_voice_log_view(voice_log_frame)
    
    def _create_batch_print_tab(self, parent):
        """创建批量打印管理标签页"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # 控制面板
        control_frame = ttk.LabelFrame(parent, text="批量打印控制", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 批量打印控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Button(button_frame, text="暂停批量打印", 
                  command=self._pause_batch_print, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="恢复批量打印", 
                  command=self._resume_batch_print, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清理已完成批次", 
                  command=self._cleanup_completed_batches, width=15).pack(side=tk.LEFT, padx=5)
        
        # 统计信息
        stats_frame = ttk.LabelFrame(control_frame, text="统计信息", padding="5")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.batch_stats_labels = {}
        stats_info = [
            ("队列大小", "queue_size"),
            ("活跃批次", "active_batches"),
            ("已完成批次", "completed_batches"),
            ("工作线程", "worker_count")
        ]
        
        for i, (label, key) in enumerate(stats_info):
            ttk.Label(stats_frame, text=f"{label}:").grid(row=0, column=i*2, sticky=tk.W, padx=(0, 5))
            self.batch_stats_labels[key] = ttk.Label(stats_frame, text="0", foreground="blue")
            self.batch_stats_labels[key].grid(row=0, column=i*2+1, sticky=tk.W, padx=(0, 20))
        
        # 批次列表和进度显示
        main_frame = ttk.Frame(parent)
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 创建Notebook用于不同视图
        batch_notebook = ttk.Notebook(main_frame)
        batch_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 活跃批次
        active_frame = ttk.Frame(batch_notebook)
        batch_notebook.add(active_frame, text="活跃批次")
        self._create_active_batch_view(active_frame)
        
        # 批次历史
        history_frame = ttk.Frame(batch_notebook)
        batch_notebook.add(history_frame, text="批次历史")
        self._create_batch_history_view(history_frame)
    

        
    def _create_task_list(self, parent):
        """创建任务列表"""
        # 创建Treeview
        columns = ('状态', '文件夹', '尺寸', '张数', '打印机', '预置', '创建时间')
        self.task_tree = ttk.Treeview(parent, columns=columns, show='tree headings', height=15)
        
        # 设置列
        self.task_tree.heading('#0', text='ID')
        self.task_tree.column('#0', width=50)
        
        for col in columns:
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=100)
            
        # 设置特定列的宽度
        self.task_tree.column('文件夹', width=300)
        self.task_tree.column('创建时间', width=150)
        
        # 滚动条
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.task_tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.task_tree.xview)
        self.task_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.task_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 右键菜单
        self.task_menu = tk.Menu(self.task_tree, tearoff=0)
        self.task_menu.add_command(label="重新排队", command=self._requeue_task)
        self.task_menu.add_separator()
        self.task_menu.add_command(label="清除已完成", command=self._clear_completed_tasks)
        
        self.task_tree.bind("<Button-3>", self._show_task_menu)
        
    def _create_log_view(self, parent):
        """创建日志视图"""
        # 创建文本框
        self.log_text = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置标签样式
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('ERROR', foreground='red')
        self.log_text.tag_config('DEBUG', foreground='gray')
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 控制按钮
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(control_frame, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存日志", command=self._save_log).pack(side=tk.LEFT, padx=5)
        
    def _create_record_view(self, parent):
        """创建打印记录视图"""
        # 创建Treeview
        columns = ('开始时间', '结束时间', '耗时', '文件夹', '打印数量', '预置', '打印机')
        self.record_tree = ttk.Treeview(parent, columns=columns, show='tree headings', height=15)
        
        # 设置列
        self.record_tree.heading('#0', text='序号')
        self.record_tree.column('#0', width=50)
        
        for col in columns:
            self.record_tree.heading(col, text=col)
            self.record_tree.column(col, width=100)
            
        # 设置特定列的宽度
        self.record_tree.column('文件夹', width=300)
        self.record_tree.column('开始时间', width=150)
        self.record_tree.column('结束时间', width=150)
        
        # 滚动条
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.record_tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.record_tree.xview)
        self.record_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.record_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 控制按钮
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(control_frame, text="刷新", command=self._refresh_records).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="导出CSV", command=self._export_records).pack(side=tk.LEFT, padx=5)
        
        # 初始加载记录
        self._refresh_records()
        
    def _create_status_bar(self, parent):
        """创建状态栏"""
        status_bar = ttk.Frame(parent)
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.status_bar_label = ttk.Label(status_bar, text="就绪", relief=tk.SUNKEN)
        self.status_bar_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.time_label = ttk.Label(status_bar, text="", relief=tk.SUNKEN, width=20)
        self.time_label.pack(side=tk.RIGHT)
        
    def _setup_logging(self):
        """设置日志处理器"""
        # 获取根日志记录器
        root_logger = logging.getLogger()
        
        # 为文件夹操作相关的模块设置日志处理器（显示在文件夹操作日志）
        folder_modules = [
            'folder_monitor',
            'folder_manager',
            'task_manager',
            'config_manager'
        ]
        
        # 添加一个自动滚动变量（如果不存在）
        if not hasattr(self, 'auto_scroll_var'):
            self.auto_scroll_var = tk.BooleanVar(value=True)
        
        if hasattr(self, 'folder_log_text'):
            for module_name in folder_modules:
                module_logger = logging.getLogger(module_name)
                folder_handler = UILogHandler(self.folder_log_text, self.auto_scroll_var)
                folder_handler.setLevel(logging.INFO)
                folder_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                folder_handler.setFormatter(folder_formatter)
                module_logger.addHandler(folder_handler)
                module_logger.setLevel(logging.INFO)
        
        # 为异常处理器设置专门的日志处理器（捕获异常相关的WARNING信息）
        # 注意：这个处理器只捕获WARNING及以上级别的日志，不影响INFO级别日志的分类
        exception_modules = ['enhanced_exception_handler', 'task_dispatcher', 'folder_manager', 'print_system', 'batch_print_manager']
        if hasattr(self, 'exception_log_text'):
            for module_name in exception_modules:
                exception_logger = logging.getLogger(module_name)
                exception_handler = UILogHandler(self.exception_log_text, self.auto_scroll_var)
                exception_handler.setLevel(logging.WARNING)  # 只显示警告和错误
                exception_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                exception_handler.setFormatter(exception_formatter)
                exception_logger.addHandler(exception_handler)
                # WARNING级别的日志会同时显示在异常日志和其他对应的日志中
        
        # 为播报系统设置专门的日志处理器
        voice_logger = logging.getLogger('voice_announcer')
        if hasattr(self, 'voice_log_text'):
            voice_handler = UILogHandler(self.voice_log_text)
            voice_handler.setLevel(logging.INFO)
            voice_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            voice_handler.setFormatter(voice_formatter)
            voice_logger.addHandler(voice_handler)
            voice_logger.setLevel(logging.INFO)
        
        # 为打印机相关模块设置专门的日志处理器（显示在打印机状态监控日志）
        printer_modules = [
            'printer_manager',
            'print_system',
            'print_executor',
            'batch_print_manager',
            'task_dispatcher'
        ]
        
        if hasattr(self, 'printer_status_log_text'):
            for module_name in printer_modules:
                printer_logger = logging.getLogger(module_name)
                printer_handler = UILogHandler(self.printer_status_log_text)
                printer_handler.setLevel(logging.INFO)
                printer_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                printer_handler.setFormatter(printer_formatter)
                printer_logger.addHandler(printer_handler)
                printer_logger.setLevel(logging.INFO)
        
        # 系统日志处理器初始化完成
        logging.getLogger('print_system').info("日志处理器设置完成")
        
    def _start_ui_update(self):
        """启动UI更新线程"""
        self._ui_update_running = True
        update_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
        update_thread.start()
        
    def _ui_update_loop(self):
        """UI更新循环"""
        while self._ui_update_running:
            try:
                # 更新时间
                self.time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # 更新系统状态
                if self.print_system.is_running():
                    if self.print_system.is_paused():
                        self._update_system_status("已暂停", "orange")
                    else:
                        self._update_system_status("运行中", "green")
                else:
                    self._update_system_status("未启动", "gray")
                    
                # 更新其他状态
                status = self.print_system.get_system_status()
                
                # 更新监控状态
                if self.print_system.folder_monitor.is_running():
                    self.status_labels['monitor'].config(text="监控中", foreground="green")
                else:
                    self.status_labels['monitor'].config(text="未监控", foreground="gray")
                    
                # 更新语音队列
                voice_queue = status.get('voice_queue_size', 0)
                self.status_labels['voice'].config(text=str(voice_queue))
                
                # 更新任务统计（优先使用新的任务分发器）
                if hasattr(self.print_system, 'task_dispatcher'):
                    dispatcher_stats = self.print_system.task_dispatcher.get_task_stats()
                    self.status_labels['total_tasks'].config(text=str(dispatcher_stats['total']))
                    self.status_labels['completed'].config(text=str(dispatcher_stats.get('completed', 0)))
                    self.status_labels['failed'].config(text=str(dispatcher_stats.get('failed', 0) + dispatcher_stats.get('exception', 0)))
                else:
                    # 兼容旧的任务管理器
                    task_stats = status.get('task_stats', {})
                    self.status_labels['total_tasks'].config(text=str(task_stats.get('total', 0)))
                    self.status_labels['completed'].config(text=str(task_stats.get('completed', 0)))
                    self.status_labels['failed'].config(text=str(task_stats.get('failed', 0)))
                
                # 更新打印机列表
                printers = status.get('enabled_printers', [])
                if printers:
                    self.status_labels['printers'].config(text=", ".join(printers))
                else:
                    self.status_labels['printers'].config(text="无")
                
                # 更新预设配置状态（每10秒检查一次）
                self._update_preset_status()
                    
                # 更新任务列表
                self._update_task_list()
                
                # 更新批次打印显示
                self._update_batch_print_display()
                
            except Exception as e:
                logging.error(f"UI更新错误: {e}")
                
            time.sleep(1)
            
    def _update_system_status(self, text: str, color: str):
        """更新系统状态显示"""
        self.status_labels['system'].config(text=text, foreground=color)
        self.status_bar_label.config(text=f"系统状态: {text}")
    
    def _update_preset_status(self):
        """更新预设配置状态显示"""
        try:
            # 限制检查频率，避免过度消耗资源
            if not hasattr(self, '_last_preset_check'):
                self._last_preset_check = 0
            
            current_time = time.time()
            if current_time - self._last_preset_check < 10:  # 每10秒检查一次
                return
            
            self._last_preset_check = current_time
            
            # 导入预设管理器（延迟导入避免启动时的依赖问题）
            try:
                from printer_preset_manager import PrinterPresetManager
                preset_manager = PrinterPresetManager()
                
                # 检查基本配置状态
                user_config = preset_manager.load_user_config()
                presets_configured = user_config.get("presets_configured", False)
                
                if presets_configured:
                    self.status_labels['preset_config'].config(text="已配置", foreground="green")
                else:
                    self.status_labels['preset_config'].config(text="未配置", foreground="red")
                
                # 检查高级配置状态
                advanced_completed = preset_manager.is_advanced_config_completed()
                
                if advanced_completed:
                    self.status_labels['advanced_config'].config(text="已完成", foreground="green")
                else:
                    if presets_configured:
                        self.status_labels['advanced_config'].config(text="待验证", foreground="orange")
                    else:
                        self.status_labels['advanced_config'].config(text="未完成", foreground="red")
                        
            except ImportError:
                # 如果预设管理器不可用，显示未知状态
                self.status_labels['preset_config'].config(text="未知", foreground="gray")
                self.status_labels['advanced_config'].config(text="未知", foreground="gray")
            except Exception as e:
                # 检查失败时显示错误状态
                self.status_labels['preset_config'].config(text="检查失败", foreground="red")
                self.status_labels['advanced_config'].config(text="检查失败", foreground="red")
                logging.error(f"预设配置状态检查失败: {e}")
                
        except Exception as e:
            logging.error(f"更新预设配置状态失败: {e}")
        
    def _update_task_list(self):
        """更新任务列表"""
        # 检查task_tree是否存在
        if not hasattr(self, 'task_tree') or self.task_tree is None:
            return
            
        # 保存当前选中项
        selection = self.task_tree.selection()
        selected_ids = [self.task_tree.item(item)['text'] for item in selection]
        
        # 清空列表
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
            
        # 获取所有任务
        tasks = self.print_system.task_manager.get_all_tasks()
        
        # 添加任务
        for i, task in enumerate(tasks[:50]):  # 只显示最新的50个任务
            values = (
                task.status.value,
                task.folder_info.name,
                task.folder_info.size or '-',
                task.folder_info.count or '-',
                task.printer or '-',
                task.preset or '-',
                task.created_time.strftime("%H:%M:%S")
            )
            
            # 根据状态设置标签
            tags = []
            if task.status.value == "已完成":
                tags.append('completed')
            elif task.status.value == "失败":
                tags.append('failed')
            elif task.status.value == "打印中":
                tags.append('printing')
                
            item = self.task_tree.insert('', 'end', text=task.task_id[:8], values=values, tags=tags)
            
            # 恢复选中状态
            if task.task_id[:8] in selected_ids:
                self.task_tree.selection_add(item)
                
        # 设置标签样式
        self.task_tree.tag_configure('completed', foreground='green')
        self.task_tree.tag_configure('failed', foreground='red')
        self.task_tree.tag_configure('printing', foreground='blue')
        
    def _browse_monitor_path(self):
        """浏览监控路径"""
        path = filedialog.askdirectory(title="选择监控文件夹")
        if path:
            self.monitor_path_var.set(path)
            self.print_system.config_manager.set_monitor_path(path)
            
    def _start_system(self):
        """启动系统"""
        if not self.monitor_path_var.get():
            messagebox.showerror("错误", "请先设置监控路径")
            return
            
        # 禁用启动按钮，防止重复点击
        self.start_button.config(state=tk.DISABLED, text="启动中...")
        
        # 在后台线程中启动系统
        def start_in_background():
            try:
                success = self.print_system.start()
                # 在主线程中更新UI
                self.root.after(0, self._on_start_complete, success)
            except Exception as e:
                # 在主线程中显示错误
                self.root.after(0, self._on_start_error, str(e))
        
        import threading
        start_thread = threading.Thread(target=start_in_background, daemon=True)
        start_thread.start()
        
    def _on_start_complete(self, success):
        """启动完成回调"""
        if success:
            self.start_button.config(state=tk.DISABLED, text="启动系统")
            self.pause_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.NORMAL)
            self.monitor_path_entry.config(state=tk.DISABLED)
        else:
            self.start_button.config(state=tk.NORMAL, text="启动系统")
            messagebox.showerror("错误", "启动系统失败，请检查配置和日志")
            
    def _on_start_error(self, error_msg):
        """启动错误回调"""
        self.start_button.config(state=tk.NORMAL, text="启动系统")
        messagebox.showerror("错误", f"启动系统时发生异常: {error_msg}")
        
    def _pause_system(self):
        """暂停/恢复系统"""
        if self.print_system.is_paused():
            self.print_system.resume()
            self.pause_button.config(text="暂停")
        else:
            self.print_system.pause()
            self.pause_button.config(text="恢复")
            
    def _stop_system(self):
        """停止系统"""
        if messagebox.askyesno("确认", "确定要停止系统吗？"):
            # 禁用停止按钮，防止重复点击
            self.stop_button.config(state=tk.DISABLED, text="停止中...")
            
            # 在后台线程中停止系统
            def stop_in_background():
                try:
                    self.print_system.stop()
                    # 在主线程中更新UI
                    self.root.after(0, self._on_stop_complete)
                except Exception as e:
                    # 在主线程中显示错误
                    self.root.after(0, self._on_stop_error, str(e))
            
            import threading
            stop_thread = threading.Thread(target=stop_in_background, daemon=True)
            stop_thread.start()
    
    def _on_stop_complete(self):
        """停止完成回调"""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="暂停")
        self.stop_button.config(state=tk.DISABLED, text="停止系统")
        self.monitor_path_entry.config(state=tk.NORMAL)
        
    def _on_stop_error(self, error_msg):
        """停止错误回调"""
        self.stop_button.config(state=tk.NORMAL, text="停止系统")
        messagebox.showerror("错误", f"停止系统时发生异常: {error_msg}")
            
    def _open_printer_config(self):
        """打开打印机配置对话框"""
        dialog = PrinterConfigDialog(self.root, self.print_system.config_manager)
        self.root.wait_window(dialog.dialog)
    
    def _open_preset_guide(self):
        """打开预设配置引导工具"""
        try:
            import subprocess
            import os
            
            guide_file = "预设配置引导工具.py"
            if os.path.exists(guide_file):
                subprocess.Popen(['python', guide_file], shell=True)
                self._log_message("预设配置引导工具已启动", 'INFO')
                messagebox.showinfo("成功", "预设配置引导工具已启动！\n\n请按照引导完成爱普生L8058打印机的预设配置。\n完成后可实现95%自动化打印。")
            else:
                messagebox.showerror("错误", f"未找到预设配置引导工具文件：{guide_file}\n请确保文件存在于当前目录。")
                self._log_message(f"未找到预设配置引导工具文件：{guide_file}", 'ERROR')
        except Exception as e:
            error_msg = f"启动预设配置引导工具失败: {e}"
            self._log_message(error_msg, 'ERROR')
            messagebox.showerror("错误", error_msg)
    
    def _open_config_checker(self):
        """打开配置状态检查工具"""
        try:
            import subprocess
            import os
            
            checker_file = "配置状态检查工具.py"
            if os.path.exists(checker_file):
                subprocess.Popen(['python', checker_file], shell=True)
                self._log_message("配置状态检查工具已启动", 'INFO')
                messagebox.showinfo("成功", "配置状态检查工具已启动！\n\n该工具将检查您的预设配置状态，\n提供问题诊断和修复建议。")
            else:
                messagebox.showerror("错误", f"未找到配置状态检查工具文件：{checker_file}\n请确保文件存在于当前目录。")
                self._log_message(f"未找到配置状态检查工具文件：{checker_file}", 'ERROR')
        except Exception as e:
            error_msg = f"启动配置状态检查工具失败: {e}"
            self._log_message(error_msg, 'ERROR')
            messagebox.showerror("错误", error_msg)
        
    def _toggle_preprocessing(self):
        """切换预处理开关"""
        enabled = self.preprocess_var.get()
        self.print_system.config_manager.set_preprocessing_enabled(enabled)
        
    def _update_wait_time(self):
        """更新等待时间"""
        wait_time = self.wait_time_var.get()
        self.print_system.config_manager.set_wait_time(wait_time)
        # 更新自动启用按钮的文本
        if hasattr(self, 'auto_enable_checkbox'):
            self.auto_enable_checkbox.configure(text=f"自动启用打印机（{wait_time}秒倒计时）")
        
    def _show_task_menu(self, event):
        """显示任务右键菜单"""
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)
            self.task_menu.post(event.x_root, event.y_root)
            
    def _requeue_task(self):
        """重新排队任务"""
        selection = self.task_tree.selection()
        if selection:
            task_id = self.task_tree.item(selection[0])['text']
            # 需要完整的task_id
            tasks = self.print_system.task_manager.get_all_tasks()
            for task in tasks:
                if task.task_id.startswith(task_id):
                    self.print_system.task_manager.requeue_task(task.task_id)
                    break
                    
    def _clear_completed_tasks(self):
        """清除已完成的任务"""
        self.print_system.task_manager.clear_completed_tasks()
        
    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def _save_log(self):
        """保存日志"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("成功", "日志已保存")
            
    def _refresh_records(self):
        """刷新打印记录"""
        # 清空列表
        for item in self.record_tree.get_children():
            self.record_tree.delete(item)
            
        # 读取日志
        logs = self.print_system.log_manager.read_logs(limit=100)
        
        # 添加记录
        for i, log in enumerate(logs):
            if log.get('type') == 'normal':
                values = (
                    log.get('实际开始时间', ''),
                    log.get('打印结束时间', ''),
                    log.get('打印耗时', '') + '秒',
                    log.get('文件夹名称', ''),
                    f"{log.get('实际打印数量', '')}/{log.get('下发数量', '')}",
                    log.get('预置名称', ''),
                    log.get('打印机名称', '')
                )
                self.record_tree.insert('', 'end', text=str(i+1), values=values)
                
    def _export_records(self):
        """导出打印记录"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                self.print_system.log_manager.export_logs(filename, 'csv')
                messagebox.showinfo("成功", "记录已导出")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
                
    def _on_closing(self):
        """窗口关闭处理"""
        if self.print_system.is_running():
            if messagebox.askyesno("确认", "系统正在运行，确定要退出吗？"):
                self._ui_update_running = False
                
                # 后台停止系统，避免阻塞UI
                def stop_and_close():
                    try:
                        self.print_system.stop()
                    except Exception as e:
                        logging.error(f"关闭时停止系统失败: {e}")
                    finally:
                        # 确保窗口最终会关闭
                        self.root.after(0, self.root.destroy)
                
                import threading
                stop_thread = threading.Thread(target=stop_and_close, daemon=True)
                stop_thread.start()
                
                # 设置超时关闭
                self.root.after(5000, self.root.destroy)  # 5秒后强制关闭
        else:
            self._ui_update_running = False
            self.root.destroy()
            
    def run(self):
        """运行主窗口"""
        self.root.mainloop()

    # =================新增的三大系统方法=================
    
    def _create_folder_log_view(self, parent):
        """创建文件夹操作日志视图"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 创建文本框
        self.folder_log_text = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.folder_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # 添加右键菜单
        folder_log_menu = tk.Menu(self.folder_log_text, tearoff=0)
        folder_log_menu.add_command(label="清空日志", command=self._clear_folder_log)
        folder_log_menu.add_command(label="保存日志", command=self._save_folder_log)
        
        def show_folder_log_menu(event):
            folder_log_menu.post(event.x_root, event.y_root)
        
        self.folder_log_text.bind("<Button-3>", show_folder_log_menu)
    
    def _create_exception_log_view(self, parent):
        """创建异常日志视图"""
        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 创建文本框
        self.exception_log_text = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.exception_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # 添加右键菜单
        exception_log_menu = tk.Menu(self.exception_log_text, tearoff=0)
        exception_log_menu.add_command(label="清空日志", command=self._clear_exception_log)
        exception_log_menu.add_command(label="保存日志", command=self._save_exception_log)
        
        def show_exception_log_menu(event):
            exception_log_menu.post(event.x_root, event.y_root)
        
        self.exception_log_text.bind("<Button-3>", show_exception_log_menu)
    
    def _create_printer_status_table(self, parent):
        """创建打印机状态表格"""
        # 表格框架
        table_frame = ttk.LabelFrame(parent, text="打印机状态与配置", padding="10")
        table_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ('状态', '编号', '纸张大小', '当前状态', '任务数', '最后任务时间')
        self.printer_status_tree = ttk.Treeview(table_frame, columns=columns, show='tree headings', height=15)
        
        # 设置列标题和宽度
        self.printer_status_tree.heading('#0', text='打印机名称')
        self.printer_status_tree.column('#0', width=200, minwidth=150)
        
        column_widths = {'状态': 80, '编号': 60, '纸张大小': 80, '当前状态': 100, '任务数': 80, '最后任务时间': 150}
        for col in columns:
            self.printer_status_tree.heading(col, text=col)
            self.printer_status_tree.column(col, width=column_widths.get(col, 100), minwidth=60)
        
        # 添加滚动条
        printer_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.printer_status_tree.yview)
        self.printer_status_tree.configure(yscrollcommand=printer_scrollbar.set)
        
        # 放置组件
        self.printer_status_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        printer_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def _create_voice_log_view(self, parent):
        """创建播报日志视图"""
        # 创建文本框
        self.voice_log_text = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.voice_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加右键菜单
        voice_log_menu = tk.Menu(self.voice_log_text, tearoff=0)
        voice_log_menu.add_command(label="清空日志", command=self._clear_voice_log)
        voice_log_menu.add_command(label="保存日志", command=self._save_voice_log)
        
        def show_voice_log_menu(event):
            voice_log_menu.post(event.x_root, event.y_root)
        
        self.voice_log_text.bind("<Button-3>", show_voice_log_menu)
    
    # 系统控制方法
    def _start_folder_system(self):
        """启动文件夹监控系统"""
        try:
            monitor_path = self.print_system.config_manager.get_monitor_path()
            if not monitor_path:
                messagebox.showerror("错误", "请先设置监控路径")
                return
                
            if not self.print_system.folder_monitor.is_running():
                self.print_system.folder_monitor.start(monitor_path)
                self._log_to_folder_log("文件夹监控系统已启动")
            else:
                self._log_to_folder_log("文件夹监控系统已在运行")
                
        except Exception as e:
            self._log_to_folder_log(f"启动文件夹监控系统失败: {e}")
            messagebox.showerror("错误", f"启动文件夹监控系统失败: {e}")
            
    def _stop_folder_system(self):
        """停止文件夹监控系统"""
        try:
            if self.print_system.folder_monitor.is_running():
                self.print_system.folder_monitor.stop()
                self._log_to_folder_log("文件夹监控系统已停止")
            else:
                self._log_to_folder_log("文件夹监控系统未在运行")
                
        except Exception as e:
            self._log_to_folder_log(f"停止文件夹监控系统失败: {e}")
            messagebox.showerror("错误", f"停止文件夹监控系统失败: {e}")
    
    def _start_voice_system(self):
        """启动语音系统"""
        def start_voice_in_background():
            try:
                # 立即禁用启动按钮，启用停止按钮
                self.root.after(0, lambda: (
                    self.voice_start_btn.config(state=tk.DISABLED),
                    self.voice_stop_btn.config(state=tk.NORMAL)
                ))
                
                success = self.print_system.independent_voice_system.start()
                if success:
                    self._log_to_voice_log("语音系统已启动")
                else:
                    self._log_to_voice_log("语音系统启动失败")
                    # 恢复按钮状态
                    self.root.after(0, lambda: (
                        self.voice_start_btn.config(state=tk.NORMAL),
                        self.voice_stop_btn.config(state=tk.DISABLED)
                    ))
            except Exception as e:
                self._log_to_voice_log(f"启动语音系统失败: {e}")
                # 恢复按钮状态
                self.root.after(0, lambda: (
                    self.voice_start_btn.config(state=tk.NORMAL),
                    self.voice_stop_btn.config(state=tk.DISABLED)
                ))
        
        threading.Thread(target=start_voice_in_background, daemon=True).start()
        
    def _stop_voice_system(self):
        """停止语音系统"""
        def stop_voice_in_background():
            try:
                # 立即禁用停止按钮，启用启动按钮
                self.root.after(0, lambda: (
                    self.voice_stop_btn.config(state=tk.DISABLED),
                    self.voice_start_btn.config(state=tk.NORMAL)
                ))
                
                success = self.print_system.independent_voice_system.stop()
                if success:
                    self._log_to_voice_log("语音系统已停止")
                else:
                    self._log_to_voice_log("语音系统停止失败")
            except Exception as e:
                self._log_to_voice_log(f"停止语音系统失败: {e}")
        
        threading.Thread(target=stop_voice_in_background, daemon=True).start()
        
    def _test_voice(self):
        """测试语音播报"""
        def test_voice_in_background():
            try:
                # 确保语音系统运行
                if not self.print_system.independent_voice_system.is_running():
                    self.print_system.independent_voice_system.start()
                
                # 播报测试消息
                self.print_system.independent_voice_system.announce("播报系统测试正常")
                self._log_to_voice_log("语音测试播报完成")
            except Exception as e:
                self._log_to_voice_log(f"语音测试失败: {e}")
        
        threading.Thread(target=test_voice_in_background, daemon=True).start()
    
    def _refresh_printer_list(self):
        """刷新打印机列表"""
        try:
            self._update_printer_status_table()
            
            # 更新第三阶段新功能显示
            if hasattr(self, 'batch_stats_labels'):
                self._update_batch_print_display()
            
            self._log_to_folder_log("已刷新打印机列表")
            
        except Exception as e:
            messagebox.showerror("错误", f"刷新打印机列表失败: {e}")
    
    def _batch_enable_printers(self):
        """批量启用打印机"""
        try:
            # 获取所有打印机
            all_printers = self.print_system.printer_manager.get_all_printers()
            enabled_count = 0
            
            for printer_name in all_printers:
                # 获取现有配置或创建默认配置
                config = self.print_system.config_manager.get_printer_config(printer_name) or {}
                
                # 如果打印机未启用，则启用它
                if not config.get('enabled', False):
                    # 设置默认配置
                    default_config = {
                        'enabled': True,
                        'printer_id': enabled_count + 1,
                        'paper_size': '5寸' if '虚拟' in printer_name else '6寸',
                        'modes': ['拍立得']
                    }
                    
                    self.print_system.config_manager.set_printer_config(printer_name, default_config)
                    enabled_count += 1
            
            # 刷新显示
            self._update_printer_status_table()
            messagebox.showinfo("成功", f"已启用 {enabled_count} 台打印机")
            
        except Exception as e:
            messagebox.showerror("错误", f"批量启用打印机失败: {e}")
    
    def _batch_disable_printers(self):
        """批量禁用打印机"""
        try:
            # 获取所有打印机
            all_printers = self.print_system.printer_manager.get_all_printers()
            disabled_count = 0
            
            for printer_name in all_printers:
                config = self.print_system.config_manager.get_printer_config(printer_name)
                
                # 如果打印机已启用，则禁用它
                if config and config.get('enabled', False):
                    config['enabled'] = False
                    self.print_system.config_manager.set_printer_config(printer_name, config)
                    disabled_count += 1
            
            # 刷新显示
            self._update_printer_status_table()
            messagebox.showinfo("成功", f"已禁用 {disabled_count} 台打印机")
            
        except Exception as e:
            messagebox.showerror("错误", f"批量禁用打印机失败: {e}")
    
    # 日志记录方法
    def _log_to_folder_log(self, message):
        """添加文件夹操作日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'folder_log_text'):
            self.root.after(0, lambda: self._append_to_text_widget(self.folder_log_text, log_message))
    
    def _log_to_exception_log(self, message):
        """添加异常日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'exception_log_text'):
            self.root.after(0, lambda: self._append_to_text_widget(self.exception_log_text, log_message))
    
    def _log_to_voice_log(self, message):
        """添加播报日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'voice_log_text'):
            self.root.after(0, lambda: self._append_to_text_widget(self.voice_log_text, log_message))
    
    def _append_to_text_widget(self, widget, message):
        """向文本组件添加消息"""
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, message)
        widget.see(tk.END)
        widget.config(state=tk.DISABLED)
    
    def _update_printer_status_table(self):
        """更新打印机状态表格"""
        try:
            # 清空现有项目
            for item in self.printer_status_tree.get_children():
                self.printer_status_tree.delete(item)
            
            # 获取所有打印机
            all_printers = self.print_system.printer_manager.get_all_printers()
            
            for printer_name in all_printers:
                # 获取配置信息
                config = self.print_system.config_manager.get_printer_config(printer_name) or {}
                is_enabled = config.get('enabled', False)
                paper_size = config.get('paper_size', '未配置')
                printer_id = config.get('printer_id', 0)
                
                # 获取当前状态
                try:
                    status = self.print_system.printer_manager.get_printer_status(printer_name)
                    status_text = "在线" if status else "离线"
                except:
                    status_text = "未知"
                
                # 插入到表格
                self.printer_status_tree.insert(
                    '', 'end',
                    text=printer_name,
                    values=(
                        "启用" if is_enabled else "禁用",
                        printer_id if is_enabled else "",
                        paper_size if is_enabled else "",
                        status_text,
                        "0",  # 当前任务数，需要从任务管理器获取
                        "无"  # 最后任务时间，需要从任务管理器获取
                    )
                )
        except Exception as e:
            logging.error(f"更新打印机状态表格失败: {e}")
    
    # 日志清空和保存方法
    def _clear_folder_log(self):
        """清空文件夹日志"""
        self.folder_log_text.config(state=tk.NORMAL)
        self.folder_log_text.delete(1.0, tk.END)
        self.folder_log_text.config(state=tk.DISABLED)
    
    def _save_folder_log(self):
        """保存文件夹日志"""
        self._save_text_to_file(self.folder_log_text, "文件夹操作日志")
    
    def _clear_exception_log(self):
        """清空异常日志"""
        self.exception_log_text.config(state=tk.NORMAL)
        self.exception_log_text.delete(1.0, tk.END)
        self.exception_log_text.config(state=tk.DISABLED)
    
    def _save_exception_log(self):
        """保存异常日志"""
        self._save_text_to_file(self.exception_log_text, "异常日志")
    
    def _clear_voice_log(self):
        """清空播报日志"""
        self.voice_log_text.config(state=tk.NORMAL)
        self.voice_log_text.delete(1.0, tk.END)
        self.voice_log_text.config(state=tk.DISABLED)
    
    def _save_voice_log(self):
        """保存播报日志"""
        self._save_text_to_file(self.voice_log_text, "播报日志")
    
    def _save_text_to_file(self, text_widget, log_type):
        """保存文本组件内容到文件"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                title=f"保存{log_type}"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    content = text_widget.get(1.0, tk.END)
                    f.write(content)
                messagebox.showinfo("成功", f"{log_type}已保存到: {filename}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存{log_type}失败: {e}")
    
    # =================第三阶段新增方法=================
    
    def _pause_batch_print(self):
        """暂停批量打印"""
        try:
            if hasattr(self.print_system, 'batch_print_manager'):
                self.print_system.batch_print_manager.pause()
                messagebox.showinfo("成功", "已暂停批量打印")
                self._update_batch_print_display()
        except Exception as e:
            messagebox.showerror("错误", f"暂停批量打印失败: {e}")
    
    def _resume_batch_print(self):
        """恢复批量打印"""
        try:
            if hasattr(self.print_system, 'batch_print_manager'):
                self.print_system.batch_print_manager.resume()
                messagebox.showinfo("成功", "已恢复批量打印")
                self._update_batch_print_display()
        except Exception as e:
            messagebox.showerror("错误", f"恢复批量打印失败: {e}")
    
    def _cleanup_completed_batches(self):
        """清理已完成的批次"""
        try:
            if hasattr(self.print_system, 'batch_print_manager'):
                self.print_system.batch_print_manager.cleanup_completed()
                messagebox.showinfo("成功", "已清理完成的批次")
                self._update_batch_print_display()
        except Exception as e:
            messagebox.showerror("错误", f"清理批次失败: {e}")
    
    def _create_active_batch_view(self, parent):
        """创建活跃批次视图"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 活跃批次树
        columns = ('状态', '进度', '总文件', '已完成', '失败', '开始时间')
        self.active_batch_tree = ttk.Treeview(parent, columns=columns, show='tree headings', height=10)
        
        # 设置列标题和宽度
        self.active_batch_tree.heading('#0', text='批次名称')
        self.active_batch_tree.column('#0', width=200, minwidth=150)
        
        column_widths = {'状态': 80, '进度': 80, '总文件': 60, '已完成': 60, '失败': 50, '开始时间': 150}
        for col in columns:
            self.active_batch_tree.heading(col, text=col)
            self.active_batch_tree.column(col, width=column_widths.get(col, 80), minwidth=50)
        
        # 添加滚动条
        batch_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.active_batch_tree.yview)
        self.active_batch_tree.configure(yscrollcommand=batch_scrollbar.set)
        
        # 放置组件
        self.active_batch_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        batch_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def _create_batch_history_view(self, parent):
        """创建批次历史视图"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 历史批次树
        columns = ('状态', '总文件', '已完成', '失败', '开始时间', '结束时间', '耗时')
        self.history_batch_tree = ttk.Treeview(parent, columns=columns, show='tree headings', height=10)
        
        # 设置列标题和宽度
        self.history_batch_tree.heading('#0', text='批次名称')
        self.history_batch_tree.column('#0', width=200, minwidth=150)
        
        column_widths = {'状态': 80, '总文件': 60, '已完成': 60, '失败': 50, '开始时间': 120, '结束时间': 120, '耗时': 80}
        for col in columns:
            self.history_batch_tree.heading(col, text=col)
            self.history_batch_tree.column(col, width=column_widths.get(col, 80), minwidth=50)
        
        # 添加滚动条
        history_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.history_batch_tree.yview)
        self.history_batch_tree.configure(yscrollcommand=history_scrollbar.set)
        
        # 放置组件
        self.history_batch_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        history_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def _update_batch_print_display(self):
        """更新批量打印显示"""
        try:
            if not hasattr(self.print_system, 'batch_print_manager'):
                return
            
            # 更新统计信息
            active_count = len(self.print_system.batch_print_manager.active_batches)
            completed_count = len(self.print_system.batch_print_manager.completed_batches)
            
            if hasattr(self, 'batch_stats_labels'):
                self.batch_stats_labels.get('active_batches', ttk.Label()).config(text=str(active_count))
                self.batch_stats_labels.get('completed_batches', ttk.Label()).config(text=str(completed_count))
            
            # 更新活跃批次
            self._update_active_batches()
            
            # 更新历史批次
            self._update_batch_history()
            
        except Exception as e:
            logging.error(f"更新批量打印显示失败: {e}")
    
    def _update_active_batches(self):
        """更新活跃批次显示"""
        try:
            # 检查控件是否存在
            if not hasattr(self, 'active_batch_tree') or self.active_batch_tree is None:
                return
                
            # 清空当前显示
            for item in self.active_batch_tree.get_children():
                self.active_batch_tree.delete(item)
            
            if not hasattr(self.print_system, 'batch_print_manager'):
                return
                
            # 获取活跃批次
            for batch_id, batch in self.print_system.batch_print_manager.active_batches.items():
                values = (
                    batch.status.value,
                    f"{batch.progress_percentage:.1f}%",
                    str(batch.total_items),
                    str(batch.completed_items),
                    str(batch.total_items - batch.completed_items),
                    batch.start_time.strftime("%H:%M:%S") if batch.start_time else ""
                )
                self.active_batch_tree.insert('', 'end', text=batch.folder_name, values=values)
                
        except Exception as e:
            logging.error(f"更新活跃批次失败: {e}")
    
    def _update_batch_history(self):
        """更新批次历史显示"""
        try:
            # 检查控件是否存在
            if not hasattr(self, 'history_batch_tree') or self.history_batch_tree is None:
                return
                
            # 清空当前显示
            for item in self.history_batch_tree.get_children():
                self.history_batch_tree.delete(item)
            
            if not hasattr(self.print_system, 'batch_print_manager'):
                return
            
            # 获取历史批次
            completed_batches = self.print_system.batch_print_manager.completed_batches
            history_batches = completed_batches[-10:] if completed_batches else []
            
            for batch in history_batches:
                duration = ""
                if batch.start_time and batch.end_time:
                    delta = batch.end_time - batch.start_time
                    duration = f"{delta.total_seconds():.1f}s"
                
                values = (
                    batch.status.value,
                    str(batch.total_items),
                    str(batch.completed_items),
                    str(batch.total_items - batch.completed_items),
                    batch.start_time.strftime("%H:%M:%S") if batch.start_time else "",
                    batch.end_time.strftime("%H:%M:%S") if batch.end_time else "",
                    duration
                )
                self.history_batch_tree.insert('', 'end', text=batch.folder_name, values=values)
                
        except Exception as e:
            logging.error(f"更新批次历史失败: {e}")

    def _update_voice_buttons(self, is_running):
        """更新语音系统按钮状态"""
        if is_running:
            self.voice_start_btn.config(state=tk.DISABLED)
            self.voice_stop_btn.config(state=tk.NORMAL)
        else:
            self.voice_start_btn.config(state=tk.NORMAL)
            self.voice_stop_btn.config(state=tk.DISABLED)

    def _log_to_printer_status_log(self, message):
        """添加打印机状态监控日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'printer_status_log_text'):
            self.root.after(0, lambda: self._append_to_text_widget(self.printer_status_log_text, log_message))
    

    def _clear_printer_status_log(self):
        """清空打印机状态监控日志"""
        if hasattr(self, 'printer_status_log_text'):
            self.printer_status_log_text.delete(1.0, tk.END)

    def _save_printer_status_log(self):
        """保存打印机状态监控日志"""
        if hasattr(self, 'printer_status_log_text'):
            self._save_text_to_file(self.printer_status_log_text, "打印机状态监控日志")

class UILogHandler(logging.Handler):
    """UI日志处理器"""
    
    def __init__(self, text_widget, auto_scroll_var=None):
        super().__init__()
        self.text_widget = text_widget
        self.auto_scroll_var = auto_scroll_var
        
    def emit(self, record):
        """发送日志记录到UI"""
        msg = self.format(record)
        tag = record.levelname
        
        # 在主线程中更新UI
        self.text_widget.after(0, self._append_log, msg, tag)
        
    def _append_log(self, msg, tag):
        """添加日志到文本框"""
        self.text_widget.insert(tk.END, msg + '\n', tag)
        
        # 检查是否需要自动滚动
        should_scroll = True
        if self.auto_scroll_var:
            should_scroll = self.auto_scroll_var.get()
        
        if should_scroll:
            self.text_widget.see(tk.END)
        
        # 限制日志行数
        lines = int(self.text_widget.index('end-1c').split('.')[0])
        if lines > 1000:
            self.text_widget.delete('1.0', '2.0')


# 主程序入口
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建并运行主窗口
    app = MainWindow()
    app.run() 