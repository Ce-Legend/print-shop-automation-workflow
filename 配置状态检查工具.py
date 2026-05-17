"""
配置状态检查和用户提醒工具
监控预设配置状态，提供用户友好的配置指导和故障排除建议
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import logging
import win32print
from typing import Dict, List, Optional, Any, Tuple
import subprocess
import time
from datetime import datetime, timedelta
import threading
from printer_preset_manager import PrinterPresetManager


class ConfigStatusChecker:
    """配置状态检查器"""
    
    def __init__(self, show_ui: bool = True):
        self.logger = logging.getLogger(__name__)
        self.preset_manager = PrinterPresetManager()
        self.show_ui = show_ui
        
        # 配置检查项目
        self.check_items = {
            "printer_connection": "打印机连接状态",
            "epson_printer": "爱普生打印机检测", 
            "preset_config": "预设配置完成度",
            "advanced_config": "高级配置状态",
            "system_files": "系统文件完整性",
            "monitor_folder": "监控文件夹设置"
        }
        
        # 状态缓存
        self.last_check_time = None
        self.last_status = {}
        
        if show_ui:
            self.create_ui()
    
    def create_ui(self):
        """创建用户界面"""
        self.root = tk.Tk()
        self.root.title("爱普生L8058打印机配置状态检查")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 主标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        title_label = ttk.Label(
            title_frame,
            text="🔍 配置状态检查工具",
            font=('微软雅黑', 16, 'bold')
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="监控预设配置状态，提供问题解决方案",
            font=('微软雅黑', 10),
            foreground='gray'
        )
        subtitle_label.pack(pady=(5, 0))
        
        # 控制按钮区域
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=20, pady=10)
        
        # 检查按钮
        check_btn = ttk.Button(
            control_frame,
            text="🔄 立即检查",
            command=self.run_full_check,
            style='Accent.TButton'
        )
        check_btn.pack(side='left', padx=(0, 10))
        
        # 自动检查开关
        self.auto_check_var = tk.BooleanVar(value=False)
        auto_check_cb = ttk.Checkbutton(
            control_frame,
            text="自动检查 (每30秒)",
            variable=self.auto_check_var,
            command=self.toggle_auto_check
        )
        auto_check_cb.pack(side='left', padx=(0, 10))
        
        # 修复问题按钮
        fix_btn = ttk.Button(
            control_frame,
            text="🔧 修复问题",
            command=self.fix_detected_issues
        )
        fix_btn.pack(side='left', padx=(0, 10))
        
        # 打开引导工具按钮
        guide_btn = ttk.Button(
            control_frame,
            text="🎯 配置引导",
            command=self.open_guide_tool
        )
        guide_btn.pack(side='left')
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Tab 1: 状态概览
        self.create_status_tab()
        
        # Tab 2: 详细检查
        self.create_detail_tab()
        
        # Tab 3: 问题解决
        self.create_solution_tab()
        
        # 状态栏
        self.create_status_bar()
        
        # 自动检查线程
        self.auto_check_thread = None
        self.auto_check_running = False
        
        # 初始检查
        self.root.after(1000, self.run_full_check)
    
    def create_status_tab(self):
        """创建状态概览标签页"""
        status_frame = ttk.Frame(self.notebook)
        self.notebook.add(status_frame, text="📊 状态概览")
        
        # 总体状态显示
        overall_frame = ttk.LabelFrame(status_frame, text="🎯 总体状态", padding=15)
        overall_frame.pack(fill='x', padx=10, pady=10)
        
        self.overall_status_label = ttk.Label(
            overall_frame,
            text="正在检查...",
            font=('微软雅黑', 12, 'bold')
        )
        self.overall_status_label.pack()
        
        # 检查项目状态
        items_frame = ttk.LabelFrame(status_frame, text="📋 检查项目", padding=15)
        items_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 创建状态表格
        columns = ('检查项目', '状态', '详情', '建议')
        self.status_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题和宽度
        for col in columns:
            self.status_tree.heading(col, text=col)
        
        self.status_tree.column('检查项目', width=150)
        self.status_tree.column('状态', width=80)
        self.status_tree.column('详情', width=200)
        self.status_tree.column('建议', width=250)
        
        # 添加滚动条
        status_scrollbar = ttk.Scrollbar(items_frame, orient='vertical', command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_tree.pack(side='left', fill='both', expand=True)
        status_scrollbar.pack(side='right', fill='y')
        
    def create_detail_tab(self):
        """创建详细检查标签页"""
        detail_frame = ttk.Frame(self.notebook)
        self.notebook.add(detail_frame, text="🔍 详细检查")
        
        # 检查结果显示
        result_frame = ttk.LabelFrame(detail_frame, text="📊 检查结果", padding=15)
        result_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.detail_text = scrolledtext.ScrolledText(result_frame, height=20, font=('Consolas', 9))
        self.detail_text.pack(fill='both', expand=True)
        
        # 导出报告按钮
        export_frame = ttk.Frame(detail_frame)
        export_frame.pack(fill='x', padx=10, pady=10)
        
        export_btn = ttk.Button(
            export_frame,
            text="📝 导出检查报告",
            command=self.export_report
        )
        export_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = ttk.Button(
            export_frame,
            text="🗑️ 清空日志",
            command=lambda: self.detail_text.delete(1.0, tk.END)
        )
        clear_btn.pack(side='left')
        
    def create_solution_tab(self):
        """创建问题解决标签页"""
        solution_frame = ttk.Frame(self.notebook)
        self.notebook.add(solution_frame, text="🔧 问题解决")
        
        # 常见问题解决方案
        solutions_frame = ttk.LabelFrame(solution_frame, text="🎯 常见问题解决方案", padding=15)
        solutions_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 解决方案列表
        solutions_text = """
🔧 常见问题及解决方案：

1️⃣ 打印机未连接
   • 检查USB连接或网络连接
   • 确认打印机驱动正确安装
   • 重启打印机和电脑

2️⃣ 预设配置未完成
   • 点击"配置引导"按钮
   • 按照引导完成4个预设配置
   • 确保预设名称完全一致

3️⃣ 高级配置状态异常
   • 运行"预设配置引导工具.py"
   • 完成验证流程
   • 检查配置文件权限

4️⃣ 系统文件缺失
   • 检查主要系统文件
   • 重新下载完整安装包
   • 联系技术支持

5️⃣ 监控文件夹设置错误
   • 确认监控文件夹路径
   • 检查文件夹权限
   • 重新配置监控路径

💡 自动修复功能：
   • 点击"修复问题"按钮尝试自动修复
   • 系统会根据检查结果自动执行修复操作
   • 部分问题需要手动处理

🆘 如需帮助：
   • 查看详细检查日志
   • 导出检查报告发送给技术支持
   • 运行配置引导工具重新配置
        """
        
        solutions_display = scrolledtext.ScrolledText(solutions_frame, height=15, font=('微软雅黑', 10))
        solutions_display.insert(tk.END, solutions_text)
        solutions_display.config(state='disabled')
        solutions_display.pack(fill='both', expand=True)
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill='x', side='bottom')
        
        self.status_label = ttk.Label(self.status_bar, text="准备就绪", relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True)
        
        # 最后检查时间
        self.last_check_label = ttk.Label(self.status_bar, text="未检查", relief='sunken')
        self.last_check_label.pack(side='right')
        
    def run_full_check(self):
        """运行完整检查"""
        try:
            self.update_status("正在检查配置状态...")
            
            # 清空之前的结果
            for item in self.status_tree.get_children():
                self.status_tree.delete(item)
            
            self.detail_text.delete(1.0, tk.END)
            
            # 开始检查
            check_time = datetime.now()
            self.detail_text.insert(tk.END, f"🔍 开始配置状态检查 - {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 执行各项检查
            results = {}
            total_score = 0
            max_score = 0
            
            for check_id, check_name in self.check_items.items():
                self.detail_text.insert(tk.END, f"🔍 检查: {check_name}\n")
                self.root.update()
                
                result = self._run_single_check(check_id)
                results[check_id] = result
                
                # 更新状态表格
                status_icon = "✅" if result['success'] else "❌"
                self.status_tree.insert('', 'end', values=(
                    check_name,
                    status_icon,
                    result['details'],
                    result['recommendation']
                ))
                
                # 计算得分
                max_score += result['max_score']
                total_score += result['score']
                
                self.detail_text.insert(tk.END, f"   {status_icon} {result['details']}\n")
                if result['recommendation']:
                    self.detail_text.insert(tk.END, f"   💡 建议: {result['recommendation']}\n")
                self.detail_text.insert(tk.END, "\n")
                
                time.sleep(0.2)  # 避免界面卡顿
            
            # 计算总体状态
            success_rate = (total_score / max_score) * 100 if max_score > 0 else 0
            overall_status = self._get_overall_status(success_rate)
            
            # 更新总体状态显示
            self.overall_status_label.config(
                text=f"{overall_status['icon']} {overall_status['text']} ({success_rate:.1f}%)",
                foreground=overall_status['color']
            )
            
            # 保存检查结果
            self.last_check_time = check_time
            self.last_status = results
            
            # 更新状态栏
            self.update_status(f"检查完成 - 总体状态: {overall_status['text']}")
            self.last_check_label.config(text=f"最后检查: {check_time.strftime('%H:%M:%S')}")
            
            # 添加总结
            self.detail_text.insert(tk.END, f"📊 检查完成 - {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.detail_text.insert(tk.END, f"总体状态: {overall_status['text']} ({success_rate:.1f}%)\n")
            self.detail_text.insert(tk.END, f"得分: {total_score}/{max_score}\n\n")
            
            # 如果有问题，显示修复建议
            if success_rate < 100:
                self.detail_text.insert(tk.END, "🔧 发现问题，建议:\n")
                self.detail_text.insert(tk.END, "• 点击「修复问题」按钮尝试自动修复\n")
                self.detail_text.insert(tk.END, "• 查看「问题解决」标签页获取详细指导\n")
                self.detail_text.insert(tk.END, "• 运行「配置引导」完成缺失配置\n\n")
            
            self.detail_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"配置检查失败: {e}"
            self.logger.error(error_msg)
            self.update_status(error_msg)
            self.detail_text.insert(tk.END, f"❌ {error_msg}\n")
    
    def _run_single_check(self, check_id: str) -> Dict[str, Any]:
        """运行单项检查"""
        try:
            if check_id == "printer_connection":
                return self._check_printer_connection()
            elif check_id == "epson_printer":
                return self._check_epson_printer()
            elif check_id == "preset_config":
                return self._check_preset_config()
            elif check_id == "advanced_config":
                return self._check_advanced_config()
            elif check_id == "system_files":
                return self._check_system_files()
            elif check_id == "monitor_folder":
                return self._check_monitor_folder()
            else:
                return {
                    'success': False,
                    'details': f'未知检查项目: {check_id}',
                    'recommendation': '联系技术支持',
                    'score': 0,
                    'max_score': 10
                }
        except Exception as e:
            return {
                'success': False,
                'details': f'检查失败: {e}',
                'recommendation': '检查系统权限或重新运行',
                'score': 0,
                'max_score': 10
            }
    
    def _check_printer_connection(self) -> Dict[str, Any]:
        """检查打印机连接状态"""
        try:
            printers = [printer[2] for printer in win32print.EnumPrinters(2)]
            if not printers:
                return {
                    'success': False,
                    'details': '未检测到任何打印机',
                    'recommendation': '检查打印机连接和驱动安装',
                    'score': 0,
                    'max_score': 10
                }
            
            return {
                'success': True,
                'details': f'检测到 {len(printers)} 台打印机',
                'recommendation': '',
                'score': 10,
                'max_score': 10
            }
        except Exception as e:
            return {
                'success': False,
                'details': f'打印机检测失败: {e}',
                'recommendation': '检查系统权限和打印服务',
                'score': 0,
                'max_score': 10
            }
    
    def _check_epson_printer(self) -> Dict[str, Any]:
        """检查爱普生打印机"""
        try:
            printers = [printer[2] for printer in win32print.EnumPrinters(2)]
            epson_printers = [p for p in printers if any(keyword in p.lower() 
                            for keyword in ["epson", "爱普生", "l8058", "l1250"])]
            
            if not epson_printers:
                return {
                    'success': False,
                    'details': '未检测到爱普生打印机',
                    'recommendation': '安装爱普生L8058打印机驱动',
                    'score': 0,
                    'max_score': 15
                }
            
            return {
                'success': True,
                'details': f'检测到爱普生打印机: {", ".join(epson_printers)}',
                'recommendation': '',
                'score': 15,
                'max_score': 15
            }
        except Exception as e:
            return {
                'success': False,
                'details': f'爱普生打印机检测失败: {e}',
                'recommendation': '检查打印机驱动安装',
                'score': 0,
                'max_score': 15
            }
    
    def _check_preset_config(self) -> Dict[str, Any]:
        """检查预设配置"""
        try:
            available_presets = self.preset_manager.get_available_presets()
            user_config = self.preset_manager.load_user_config()
            
            if not user_config.get("presets_configured", False):
                return {
                    'success': False,
                    'details': '预设配置未完成',
                    'recommendation': '运行预设配置引导工具',
                    'score': 0,
                    'max_score': 20
                }
            
            return {
                'success': True,
                'details': f'预设配置已完成，支持 {len(available_presets)} 个预设',
                'recommendation': '',
                'score': 20,
                'max_score': 20
            }
        except Exception as e:
            return {
                'success': False,
                'details': f'预设配置检查失败: {e}',
                'recommendation': '重新运行配置引导工具',
                'score': 0,
                'max_score': 20
            }
    
    def _check_advanced_config(self) -> Dict[str, Any]:
        """检查高级配置状态"""
        try:
            is_completed = self.preset_manager.is_advanced_config_completed()
            
            if not is_completed:
                return {
                    'success': False,
                    'details': '高级配置未完成或验证失败',
                    'recommendation': '完成预设配置引导工具的验证流程',
                    'score': 5,
                    'max_score': 25
                }
            
            return {
                'success': True,
                'details': '高级配置已完成并验证通过',
                'recommendation': '',
                'score': 25,
                'max_score': 25
            }
        except Exception as e:
            return {
                'success': False,
                'details': f'高级配置检查失败: {e}',
                'recommendation': '重新运行配置验证',
                'score': 0,
                'max_score': 25
            }
    
    def _check_system_files(self) -> Dict[str, Any]:
        """检查系统文件完整性"""
        try:
            required_files = [
                "main.py",
                "print_system.py", 
                "printer_preset_manager.py",
                "print_executor.py",
                "config.json"
            ]
            
            missing_files = []
            for file_name in required_files:
                if not os.path.exists(file_name):
                    missing_files.append(file_name)
            
            if missing_files:
                return {
                    'success': False,
                    'details': f'缺失系统文件: {", ".join(missing_files)}',
                    'recommendation': '重新下载完整安装包',
                    'score': max(0, 15 - len(missing_files) * 3),
                    'max_score': 15
                }
            
            return {
                'success': True,
                'details': '所有系统文件完整',
                'recommendation': '',
                'score': 15,
                'max_score': 15
            }
        except Exception as e:
            return {
                'success': False,
                'details': f'系统文件检查失败: {e}',
                'recommendation': '检查文件权限',
                'score': 0,
                'max_score': 15
            }
    
    def _check_monitor_folder(self) -> Dict[str, Any]:
        """检查监控文件夹设置"""
        try:
            # 检查config.json中的监控路径设置
            config_path = "config.json"
            if not os.path.exists(config_path):
                return {
                    'success': False,
                    'details': '配置文件不存在',
                    'recommendation': '重新生成配置文件',
                    'score': 0,
                    'max_score': 15
                }
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            monitor_path = config.get("monitor_path", "")
            if not monitor_path:
                return {
                    'success': False,
                    'details': '监控文件夹路径未设置',
                    'recommendation': '配置监控文件夹路径',
                    'score': 5,
                    'max_score': 15
                }
            
            if not os.path.exists(monitor_path):
                return {
                    'success': False,
                    'details': f'监控文件夹不存在: {monitor_path}',
                    'recommendation': '创建监控文件夹或修改配置路径',
                    'score': 8,
                    'max_score': 15
                }
            
            return {
                'success': True,
                'details': f'监控文件夹配置正确: {monitor_path}',
                'recommendation': '',
                'score': 15,
                'max_score': 15
            }
        except Exception as e:
            return {
                'success': False,
                'details': f'监控文件夹检查失败: {e}',
                'recommendation': '检查配置文件权限',
                'score': 0,
                'max_score': 15
            }
    
    def _get_overall_status(self, success_rate: float) -> Dict[str, str]:
        """获取总体状态"""
        if success_rate >= 95:
            return {
                'icon': '🟢',
                'text': '配置完美',
                'color': 'green'
            }
        elif success_rate >= 80:
            return {
                'icon': '🟡',
                'text': '配置良好',
                'color': 'orange'
            }
        elif success_rate >= 60:
            return {
                'icon': '🟠',
                'text': '需要优化',
                'color': 'darkorange'
            }
        else:
            return {
                'icon': '🔴',
                'text': '需要修复',
                'color': 'red'
            }
    
    def toggle_auto_check(self):
        """切换自动检查"""
        if self.auto_check_var.get():
            self.start_auto_check()
        else:
            self.stop_auto_check()
    
    def start_auto_check(self):
        """启动自动检查"""
        if not self.auto_check_running:
            self.auto_check_running = True
            self.auto_check_thread = threading.Thread(target=self._auto_check_loop, daemon=True)
            self.auto_check_thread.start()
            self.update_status("自动检查已启动")
    
    def stop_auto_check(self):
        """停止自动检查"""
        self.auto_check_running = False
        if self.auto_check_thread:
            self.auto_check_thread.join(timeout=1)
        self.update_status("自动检查已停止")
    
    def _auto_check_loop(self):
        """自动检查循环"""
        while self.auto_check_running:
            try:
                time.sleep(30)  # 每30秒检查一次
                if self.auto_check_running:
                    self.root.after(0, self.run_full_check)
            except Exception as e:
                self.logger.error(f"自动检查出错: {e}")
    
    def fix_detected_issues(self):
        """修复检测到的问题"""
        try:
            self.update_status("正在尝试修复问题...")
            
            fixed_issues = []
            failed_fixes = []
            
            # 根据最后的检查结果执行修复
            if not self.last_status:
                messagebox.showwarning("提示", "请先运行检查再尝试修复")
                return
            
            # 修复监控文件夹问题
            if not self.last_status.get("monitor_folder", {}).get("success", True):
                try:
                    monitor_path = "监控文件夹"
                    if not os.path.exists(monitor_path):
                        os.makedirs(monitor_path)
                        fixed_issues.append("创建监控文件夹")
                except Exception as e:
                    failed_fixes.append(f"创建监控文件夹失败: {e}")
            
            # 修复配置文件问题
            if not self.last_status.get("system_files", {}).get("success", True):
                try:
                    # 尝试创建基本配置文件
                    if not os.path.exists("config.json"):
                        basic_config = {
                            "monitor_path": os.path.abspath("监控文件夹"),
                            "exception_folder": "异常文件夹",
                            "wait_time": 60,
                            "enable_preprocessing": True,
                            "printers": {},
                            "presets": {}
                        }
                        with open("config.json", 'w', encoding='utf-8') as f:
                            json.dump(basic_config, f, ensure_ascii=False, indent=2)
                        fixed_issues.append("创建基本配置文件")
                except Exception as e:
                    failed_fixes.append(f"创建配置文件失败: {e}")
            
            # 显示修复结果
            result_msg = "🔧 自动修复完成:\n\n"
            
            if fixed_issues:
                result_msg += "✅ 成功修复:\n"
                for issue in fixed_issues:
                    result_msg += f"  • {issue}\n"
                result_msg += "\n"
            
            if failed_fixes:
                result_msg += "❌ 修复失败:\n"
                for issue in failed_fixes:
                    result_msg += f"  • {issue}\n"
                result_msg += "\n"
            
            if not fixed_issues and not failed_fixes:
                result_msg += "💡 未发现可自动修复的问题\n\n"
            
            result_msg += "建议:\n"
            result_msg += "• 重新运行检查验证修复效果\n"
            result_msg += "• 对于无法自动修复的问题，请查看「问题解决」标签页\n"
            result_msg += "• 运行配置引导工具完成预设配置"
            
            messagebox.showinfo("修复结果", result_msg)
            
            # 自动重新检查
            self.root.after(1000, self.run_full_check)
            
        except Exception as e:
            error_msg = f"自动修复失败: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("错误", error_msg)
        finally:
            self.update_status("修复完成")
    
    def open_guide_tool(self):
        """打开配置引导工具"""
        try:
            if self.preset_manager.open_preset_guide():
                self.update_status("配置引导工具已启动")
                messagebox.showinfo("成功", "配置引导工具已启动！\n请按照引导完成预设配置。")
            else:
                messagebox.showerror("错误", "无法启动配置引导工具\n请确保文件存在：预设配置引导工具.py")
        except Exception as e:
            messagebox.showerror("错误", f"启动配置引导工具失败: {e}")
    
    def export_report(self):
        """导出检查报告"""
        try:
            report_content = self.detail_text.get(1.0, tk.END)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"配置检查报告_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.update_status(f"报告已导出: {filename}")
            messagebox.showinfo("成功", f"检查报告已导出到:\n{filename}")
            
        except Exception as e:
            error_msg = f"导出报告失败: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def update_status(self, message: str):
        """更新状态栏"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
            self.root.update_idletasks()
        else:
            print(f"状态: {message}")
    
    def run_ui(self):
        """运行用户界面"""
        if self.show_ui:
            try:
                self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
                self.root.mainloop()
            except Exception as e:
                self.logger.error(f"界面运行失败: {e}")
        
    def _on_closing(self):
        """窗口关闭处理"""
        self.stop_auto_check()
        self.root.destroy()
    
    def run_console_check(self) -> Dict[str, Any]:
        """运行控制台检查（无界面）"""
        results = {}
        
        print("🔍 开始配置状态检查...")
        
        for check_id, check_name in self.check_items.items():
            print(f"检查: {check_name}")
            result = self._run_single_check(check_id)
            results[check_id] = result
            
            status_icon = "✅" if result['success'] else "❌"
            print(f"  {status_icon} {result['details']}")
            if result['recommendation']:
                print(f"  💡 建议: {result['recommendation']}")
        
        # 计算总体状态
        total_score = sum(r['score'] for r in results.values())
        max_score = sum(r['max_score'] for r in results.values())
        success_rate = (total_score / max_score) * 100 if max_score > 0 else 0
        
        overall_status = self._get_overall_status(success_rate)
        print(f"\n📊 总体状态: {overall_status['text']} ({success_rate:.1f}%)")
        
        return {
            'results': results,
            'success_rate': success_rate,
            'overall_status': overall_status,
            'total_score': total_score,
            'max_score': max_score
        }


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        # 控制台模式
        checker = ConfigStatusChecker(show_ui=False)
        result = checker.run_console_check()
        return result['success_rate'] >= 80
    else:
        # 界面模式
        checker = ConfigStatusChecker(show_ui=True)
        checker.run_ui()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"配置状态检查工具启动失败: {e}")
        import traceback
        traceback.print_exc() 