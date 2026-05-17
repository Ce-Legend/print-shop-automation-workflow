import sys
import types


watchdog = types.ModuleType("watchdog")
watchdog_observers = types.ModuleType("watchdog.observers")
watchdog_events = types.ModuleType("watchdog.events")


class DummyObserver:
    def schedule(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def join(self):
        pass

    def is_alive(self):
        return False


class DummyFileSystemEventHandler:
    pass


class DummyDirCreatedEvent:
    pass


watchdog_observers.Observer = DummyObserver
watchdog_events.FileSystemEventHandler = DummyFileSystemEventHandler
watchdog_events.DirCreatedEvent = DummyDirCreatedEvent
sys.modules.setdefault("watchdog", watchdog)
sys.modules.setdefault("watchdog.observers", watchdog_observers)
sys.modules.setdefault("watchdog.events", watchdog_events)

from folder_monitor import FolderNameParser


def test_parse_standard_polaroid_folder_name():
    info = FolderNameParser.parse("【拍立得】5寸,10张 250701-123456789012345")

    assert info.size == "5寸"
    assert info.mode == "拍立得"
    assert info.count == 10
    assert info.order_id == "250701-123456789012345"


def test_parse_short_size_alias():
    info = FolderNameParser.parse("3T_拍立得_5张250703-123456789012347")

    assert info.size == "3寸"
    assert info.mode == "拍立得"
    assert info.count == 5
    assert info.order_id == "250703-123456789012347"


def test_parse_panorama_mode():
    info = FolderNameParser.parse("【全景】6寸,8张 250702-123456789012346")

    assert info.size == "6寸"
    assert info.mode == "全景"
    assert info.count == 8
