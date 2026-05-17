"""
打印机配置界面模块
提供打印机选择、启用/禁用、纸张设置等功能
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Optional

from printer_manager import PrinterManager
from config_manager import ConfigManager


class PrinterConfigDialog:
    """打印机配置对话框"""
    
    def __init__(self, parent, config_manager: ConfigManager):
        """初始化打印机配置对话框"""
        self.parent = parent
        self.config_manager = config_manager
        self.printer_manager = PrinterManager()
        self.logger = logging.getLogger(__name__)
        
        # 用于存储TreeView项目的额外数据
        self.item_data = {}
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("打印机配置")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 窗口居中
        self._center_window()
        
        # 创建UI
        self._create_ui()
        
        # 加载打印机列表
        self._load_printers()
        
        # 绑定窗口关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _center_window(self):
        """窗口居中显示"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="打印机配置", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # 打印机列表框架
        list_frame = ttk.LabelFrame(main_frame, text="可用打印机", padding="10")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview显示打印机
        columns = ('启用', '编号', '纸张大小', '状态')
        self.printer_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=15)
        
        # 设置列标题和宽度
        self.printer_tree.heading('#0', text='打印机名称')
        self.printer_tree.column('#0', width=250, minwidth=200)
        
        for col in columns:
            self.printer_tree.heading(col, text=col)
            self.printer_tree.column(col, width=100, minwidth=80)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.printer_tree.yview)
        self.printer_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.printer_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定双击事件
        self.printer_tree.bind('<Double-1>', self._on_printer_double_click)
        
        # 操作按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(button_frame, text="刷新列表", command=self._refresh_printers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="启用选中", command=self._enable_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="禁用选中", command=self._disable_selected).pack(side=tk.LEFT, padx=5)
        
        # 底部按钮框架
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=3, column=0, pady=10)
        
        ttk.Button(bottom_frame, text="保存配置", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=self._on_cancel).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def _load_printers(self):
        """加载打印机列表"""
        try:
            self.status_var.set("正在加载打印机列表...")
            self.dialog.update()
            
            # 清空现有项目
            for item in self.printer_tree.get_children():
                self.printer_tree.delete(item)
            
            # 清空项目数据
            self.item_data.clear()
            
            # 获取打印机列表
            printers = self.printer_manager.get_all_printers()
            
            # 添加打印机到树视图
            for printer_name in printers:
                # 获取打印机状态
                try:
                    status = self.printer_manager.get_printer_status(printer_name)
                    status_text = "正常" if status else "离线"
                except:
                    status_text = "未知"
                
                # 获取配置信息（包括已禁用的）
                printer_config = self.config_manager.get_printer_config(printer_name) or {}
                is_enabled = printer_config.get('enabled', False)
                paper_size = printer_config.get('paper_size', '5寸')
                printer_id = printer_config.get('printer_id', 0)
                
                # 插入到树视图
                item_id = self.printer_tree.insert(
                    '', 
                    'end', 
                    text=printer_name,
                    values=(
                        "✓" if is_enabled else "✗",
                        printer_id if is_enabled else "",
                        paper_size if is_enabled else "",
                        status_text
                    )
                )
                
                # 存储项目的额外数据
                self.item_data[item_id] = {
                    'enabled': is_enabled,
                    'printer_name': printer_name
                }
                
            self.status_var.set(f"已加载 {len(printers)} 台打印机")
            
        except Exception as e:
            self.logger.error(f"加载打印机列表失败: {e}")
            messagebox.showerror("错误", f"加载打印机列表失败:\n{e}")
            self.status_var.set("加载失败")
    
    def _refresh_printers(self):
        """刷新打印机列表"""
        self._load_printers()
    
    def _on_printer_double_click(self, event):
        """处理打印机双击事件"""
        selection = self.printer_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        printer_name = self.item_data.get(item, {}).get('printer_name', '')
        
        # 打开详细配置对话框
        self._open_detail_config(printer_name, item)
    
    def _open_detail_config(self, printer_name: str, tree_item):
        """打开详细配置对话框"""
        # 创建配置对话框
        config_dialog = tk.Toplevel(self.dialog)
        config_dialog.title(f"配置打印机: {printer_name}")
        config_dialog.geometry("400x300")
        config_dialog.resizable(False, False)
        config_dialog.grab_set()  # 模态对话框
        
        # 居中显示
        config_dialog.transient(self.dialog)
        config_dialog.update_idletasks()
        x = (config_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (config_dialog.winfo_screenheight() // 2) - (300 // 2)
        config_dialog.geometry(f"400x300+{x}+{y}")
        
        # 获取当前配置
        current_config = self.config_manager.get_printer_config(printer_name) or {
            'enabled': False,
            'paper_size': '5寸',
            'printer_id': 0
        }
        
        # 创建变量
        enabled_var = tk.BooleanVar(value=current_config.get('enabled', False))
        paper_size_var = tk.StringVar(value=current_config.get('paper_size', '5寸'))
        
        # 主框架
        main_frame = ttk.Frame(config_dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 打印机名称标签
        ttk.Label(main_frame, text=f"打印机: {printer_name}", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 启用/禁用选择
        ttk.Label(main_frame, text="状态:").grid(row=1, column=0, sticky=tk.W, pady=5)
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(status_frame, text="启用", variable=enabled_var, value=True).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(status_frame, text="禁用", variable=enabled_var, value=False).pack(side=tk.LEFT)
        
        # 纸张大小选择
        ttk.Label(main_frame, text="纸张大小:").grid(row=2, column=0, sticky=tk.W, pady=5)
        paper_size_combo = ttk.Combobox(main_frame, textvariable=paper_size_var, 
                                       values=['5寸', '6寸'], state='readonly', width=10)
        paper_size_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 当前状态显示
        ttk.Label(main_frame, text="当前状态:").grid(row=3, column=0, sticky=tk.W, pady=5)
        try:
            status = self.printer_manager.get_printer_status(printer_name)
            status_text = "在线" if status else "离线"
        except:
            status_text = "未知"
        ttk.Label(main_frame, text=status_text).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 打印机编号显示
        printer_id = current_config.get('printer_id', 0)
        if printer_id == 0 and enabled_var.get():
            printer_id = self._get_next_printer_id()
        
        ttk.Label(main_frame, text="打印机编号:").grid(row=4, column=0, sticky=tk.W, pady=5)
        id_label = ttk.Label(main_frame, text=str(printer_id) if printer_id > 0 else "未分配")
        id_label.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        def save_config():
            """保存配置"""
            try:
                new_config = {
                    'enabled': enabled_var.get(),
                    'paper_size': paper_size_var.get(),
                    'printer_id': current_config.get('printer_id', 0)
                }
                
                # 如果启用但没有编号，分配新编号
                if new_config['enabled'] and new_config['printer_id'] == 0:
                    new_config['printer_id'] = self._get_next_printer_id()
                
                # 保存配置
                self.config_manager.set_printer_config(printer_name, new_config)
                
                # 更新树视图
                current_values = self.printer_tree.item(tree_item)['values']
                status_text = current_values[3] if len(current_values) > 3 else "未知"
                
                self.printer_tree.item(tree_item, values=(
                    "✓" if new_config['enabled'] else "✗",
                    new_config['printer_id'] if new_config['enabled'] else "",
                    new_config['paper_size'] if new_config['enabled'] else "",
                    status_text
                ))
                
                # 更新项目数据
                if tree_item in self.item_data:
                    self.item_data[tree_item]['enabled'] = new_config['enabled']
                
                self.logger.info(f"打印机配置已更新: {printer_name}")
                config_dialog.destroy()
                
            except Exception as e:
                self.logger.error(f"保存打印机配置失败: {e}")
                messagebox.showerror("错误", f"保存配置失败:\n{e}")
        
        def cancel_config():
            """取消配置"""
            config_dialog.destroy()
        
        ttk.Button(button_frame, text="保存", command=save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=cancel_config).pack(side=tk.LEFT, padx=5)
        
        # 等待对话框关闭
        config_dialog.wait_window()
    
    def _enable_printer(self, printer_name: str, tree_item):
        """启用单个打印机"""
        # 获取现有配置或创建默认配置
        config = self.config_manager.get_printer_config(printer_name) or {
            'enabled': False,
            'paper_size': '5寸',
            'printer_id': 0
        }
        
        config['enabled'] = True
        # 确保每次启用都分配有效的printer_id
        if config.get('printer_id', 0) == 0:
            config['printer_id'] = self._get_next_printer_id()
        
        # 直接设置单个打印机配置
        self.config_manager.set_printer_config(printer_name, config)
        
        self.logger.info(f"启用打印机: {printer_name}, ID: {config['printer_id']}")
        
        # 更新树视图
        current_values = self.printer_tree.item(tree_item)['values']
        status_text = current_values[3] if len(current_values) > 3 else "未知"
        
        self.printer_tree.item(tree_item, values=(
            "✓",
            config['printer_id'],
            config['paper_size'],
            status_text
        ))
        
        # 更新项目数据
        if tree_item in self.item_data:
            self.item_data[tree_item]['enabled'] = True
    
    def _disable_printer(self, printer_name: str, tree_item):
        """禁用单个打印机"""
        # 获取现有配置
        config = self.config_manager.get_printer_config(printer_name)
        if config:
            config['enabled'] = False
            # 直接设置单个打印机配置
            self.config_manager.set_printer_config(printer_name, config)
        
        # 更新树视图
        current_values = self.printer_tree.item(tree_item)['values']
        status_text = current_values[3] if len(current_values) > 3 else "未知"
        
        self.printer_tree.item(tree_item, values=(
            "✗",
            "",
            "",
            status_text
        ))
        
        # 更新项目数据
        if tree_item in self.item_data:
            self.item_data[tree_item]['enabled'] = False
    
    def _enable_selected(self):
        """启用选中的打印机"""
        selection = self.printer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要启用的打印机")
            return
        
        for item in selection:
            printer_name = self.item_data.get(item, {}).get('printer_name', '')
            self._enable_printer(printer_name, item)
        
        self.status_var.set(f"已启用 {len(selection)} 台打印机")
    
    def _disable_selected(self):
        """禁用选中的打印机"""
        selection = self.printer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要禁用的打印机")
            return
        
        for item in selection:
            printer_name = self.item_data.get(item, {}).get('printer_name', '')
            self._disable_printer(printer_name, item)
        
        self.status_var.set(f"已禁用 {len(selection)} 台打印机")
    
    def _get_next_printer_id(self) -> int:
        """获取下一个可用的打印机编号"""
        all_printers = self.config_manager.get("printers", {})
        used_ids = set()
        
        for config in all_printers.values():
            if config.get('printer_id'):
                used_ids.add(config['printer_id'])
        
        # 找到第一个未使用的编号
        for i in range(1, 100):
            if i not in used_ids:
                return i
        
        return 1
    
    def _save_config(self):
        """保存配置"""
        try:
            self.config_manager.save_config()
            messagebox.showinfo("成功", "配置已保存")
            self.dialog.destroy()
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败:\n{e}")
    
    def _on_cancel(self):
        """取消配置"""
        self.dialog.destroy()
    
    def show(self):
        """显示对话框"""
        self.dialog.wait_window()


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.append('.')
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    # 显示打印机配置对话框
    dialog = PrinterConfigDialog(root, config_manager)
    dialog.show()
    
    root.destroy() 