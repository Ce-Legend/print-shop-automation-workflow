"""
日志记录模块
负责记录打印任务的详细日志到.np文件
"""
import os
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import time


class LogManager:
    """日志管理器"""
    
    def __init__(self, log_file: str = "打印日志.np"):
        """
        初始化日志管理器
        
        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._ensure_log_file()
        
    def _ensure_log_file(self):
        """确保日志文件存在，如果不存在则创建并写入标题行"""
        if not os.path.exists(self.log_file):
            header = "|".join([
                "打印下发时间",
                "实际开始时间", 
                "打印结束时间",
                "打印耗时",
                "文件夹名称",
                "下发数量",
                "实际打印数量",
                "预置名称",
                "打印机名称",
                "平均打印时间"
            ])
            self._write_line(header)
            
    def _write_line(self, line: str):
        """
        安全写入一行日志
        使用追加模式和立即刷新，避免文件锁定问题
        """
        with self._lock:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
                    f.flush()  # 立即刷新缓冲区
                    os.fsync(f.fileno())  # 强制写入磁盘
            except Exception as e:
                self.logger.error(f"写入日志失败: {e}")
                
    def log_print_task(self, task_info: Dict[str, Any]):
        """
        记录打印任务日志
        
        Args:
            task_info: 任务信息字典，应包含以下键：
                - submitted_time: 打印下发时间
                - start_time: 实际开始时间
                - end_time: 打印结束时间
                - folder_name: 文件夹名称
                - submitted_count: 下发数量
                - printed_count: 实际打印数量
                - preset_name: 预置名称
                - printer_name: 打印机名称
        """
        try:
            # 计算打印耗时
            if task_info.get('start_time') and task_info.get('end_time'):
                duration = (task_info['end_time'] - task_info['start_time']).total_seconds()
            else:
                duration = 0
                
            # 计算平均打印时间
            printed_count = task_info.get('printed_count', 0)
            avg_time = duration / printed_count if printed_count > 0 else 0
            
            # 格式化时间
            def format_time(dt):
                if isinstance(dt, datetime):
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(dt, str):
                    return dt
                else:
                    return ''
                    
            # 构建日志行
            log_line = "|".join([
                format_time(task_info.get('submitted_time', '')),
                format_time(task_info.get('start_time', '')),
                format_time(task_info.get('end_time', '')),
                f"{duration:.0f}",
                str(task_info.get('folder_name', '')),
                str(task_info.get('submitted_count', 0)),
                str(task_info.get('printed_count', 0)),
                str(task_info.get('preset_name', '')),
                str(task_info.get('printer_name', '')),
                f"{avg_time:.1f}"
            ])
            
            self._write_line(log_line)
            self.logger.info(f"任务日志已记录: {task_info.get('folder_name', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"记录打印任务日志失败: {e}")
            
    def log_error(self, error_info: Dict[str, Any]):
        """
        记录错误日志
        
        Args:
            error_info: 错误信息字典
        """
        try:
            error_line = f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {json.dumps(error_info, ensure_ascii=False)}"
            self._write_line(error_line)
        except Exception as e:
            self.logger.error(f"记录错误日志失败: {e}")
            
    def read_logs(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        读取日志记录
        
        Args:
            limit: 限制返回的记录数，None表示全部
            
        Returns:
            日志记录列表
        """
        logs = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 跳过标题行
            if lines and not lines[0].startswith('['):
                headers = lines[0].strip().split('|')
                lines = lines[1:]
            else:
                headers = [
                    "打印下发时间", "实际开始时间", "打印结束时间",
                    "打印耗时", "文件夹名称", "下发数量",
                    "实际打印数量", "预置名称", "打印机名称", "平均打印时间"
                ]
                
            # 解析日志行
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('[ERROR]'):
                    # 错误日志
                    logs.append({'type': 'error', 'content': line})
                else:
                    # 正常日志
                    parts = line.split('|')
                    if len(parts) == len(headers):
                        log_dict = dict(zip(headers, parts))
                        log_dict['type'] = 'normal'
                        logs.append(log_dict)
                        
            # 限制返回数量
            if limit:
                logs = logs[-limit:]
                
        except FileNotFoundError:
            self.logger.warning(f"日志文件不存在: {self.log_file}")
        except Exception as e:
            self.logger.error(f"读取日志失败: {e}")
            
        return logs
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取打印统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_tasks': 0,
            'total_pages': 0,
            'total_duration': 0,
            'avg_duration': 0,
            'avg_pages_per_task': 0,
            'printer_stats': {},
            'preset_stats': {},
            'daily_stats': {}
        }
        
        logs = self.read_logs()
        normal_logs = [log for log in logs if log.get('type') == 'normal']
        
        for log in normal_logs:
            try:
                # 总任务数
                stats['total_tasks'] += 1
                
                # 总页数
                printed_count = int(log.get('实际打印数量', 0))
                stats['total_pages'] += printed_count
                
                # 总耗时
                duration = float(log.get('打印耗时', 0))
                stats['total_duration'] += duration
                
                # 按打印机统计
                printer = log.get('打印机名称', '未知')
                if printer not in stats['printer_stats']:
                    stats['printer_stats'][printer] = {
                        'tasks': 0,
                        'pages': 0,
                        'duration': 0
                    }
                stats['printer_stats'][printer]['tasks'] += 1
                stats['printer_stats'][printer]['pages'] += printed_count
                stats['printer_stats'][printer]['duration'] += duration
                
                # 按预置统计
                preset = log.get('预置名称', '未知')
                if preset not in stats['preset_stats']:
                    stats['preset_stats'][preset] = {
                        'tasks': 0,
                        'pages': 0
                    }
                stats['preset_stats'][preset]['tasks'] += 1
                stats['preset_stats'][preset]['pages'] += printed_count
                
                # 按日期统计
                submit_time = log.get('打印下发时间', '')
                if submit_time:
                    date = submit_time.split(' ')[0]
                    if date not in stats['daily_stats']:
                        stats['daily_stats'][date] = {
                            'tasks': 0,
                            'pages': 0
                        }
                    stats['daily_stats'][date]['tasks'] += 1
                    stats['daily_stats'][date]['pages'] += printed_count
                    
            except Exception as e:
                self.logger.error(f"处理日志统计时出错: {e}")
                
        # 计算平均值
        if stats['total_tasks'] > 0:
            stats['avg_duration'] = stats['total_duration'] / stats['total_tasks']
            stats['avg_pages_per_task'] = stats['total_pages'] / stats['total_tasks']
            
        return stats
    
    def export_logs(self, output_file: str, format: str = 'csv'):
        """
        导出日志
        
        Args:
            output_file: 输出文件路径
            format: 导出格式 ('csv' 或 'json')
        """
        try:
            logs = self.read_logs()
            
            if format == 'csv':
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    if logs:
                        # 获取所有可能的字段
                        fieldnames = set()
                        for log in logs:
                            if log.get('type') == 'normal':
                                fieldnames.update(log.keys())
                        fieldnames.discard('type')
                        fieldnames = sorted(list(fieldnames))
                        
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for log in logs:
                            if log.get('type') == 'normal':
                                row = {k: v for k, v in log.items() if k != 'type'}
                                writer.writerow(row)
                                
            elif format == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
                    
            self.logger.info(f"日志已导出到: {output_file}")
            
        except Exception as e:
            self.logger.error(f"导出日志失败: {e}")
            raise


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建日志管理器
    log_manager = LogManager("test_log.np")
    
    # 测试记录日志
    test_task = {
        'submitted_time': datetime.now(),
        'start_time': datetime.now(),
        'end_time': datetime.now(),
        'folder_name': '5寸【拍立得留白】,10张美照250530-620547284501157',
        'submitted_count': 10,
        'printed_count': 10,
        'preset_name': '5寸拍立得',
        'printer_name': '测试打印机'
    }
    
    log_manager.log_print_task(test_task)
    
    # 测试读取日志
    logs = log_manager.read_logs()
    print(f"\n读取到 {len(logs)} 条日志")
    
    # 测试统计
    stats = log_manager.get_statistics()
    print(f"\n统计信息:")
    print(f"总任务数: {stats['total_tasks']}")
    print(f"总页数: {stats['total_pages']}")
    print(f"平均耗时: {stats['avg_duration']:.1f} 秒") 