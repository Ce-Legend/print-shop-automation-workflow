from config_manager import ConfigManager


def test_default_preset_mapping(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(str(config_path))

    assert manager.get_preset_for_size_mode("3寸", "拍立得") == "5寸拍立得"
    assert manager.get_preset_for_size_mode("5寸", "全景") == "5寸全景"
    assert manager.get_preset_for_size_mode("6寸", "拍立得") == "6寸拍立得"
