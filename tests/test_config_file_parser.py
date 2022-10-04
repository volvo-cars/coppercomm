import pytest
from unittest.mock import MagicMock, Mock, patch, sentinel

from coppercomm import config_file_parser


@patch("coppercomm.config_file_parser.Path")
@patch("os.getenv")
def test_config_file_from_variable_1(getenv_m, path_class_m):
    """When variable is a path to directory."""
    some_str_p = getenv_m.return_value
    device_config_path = path_class_m.return_value.expanduser.return_value
    device_config_path.is_file.return_value = False
    device_config_path.is_dir.return_value = True
    file_in_device_config_path = device_config_path.__truediv__.return_value
    file_in_device_config_path.is_file.return_value = True

    resp = config_file_parser._config_file_from_variable(sentinel.my_var, "my_file.json")

    assert resp is file_in_device_config_path
    device_config_path.__truediv__.assert_called_once_with("my_file.json")

@patch("coppercomm.config_file_parser.Path")
@patch("os.getenv")
def test_config_file_from_variable_1(getenv_m, path_class_m):
    """When variable is a path to a file."""
    some_str_p = getenv_m.return_value
    device_config_path = path_class_m.return_value.expanduser.return_value
    device_config_path.is_file.return_value = True

    resp = config_file_parser._config_file_from_variable(sentinel.my_var, "my_file.json")
    assert resp is device_config_path
    device_config_path.__truediv__.assert_not_called()


@patch("coppercomm.config_file_parser._config_file_from_variable")
@patch("json.load")
def test_load_config_1(jsload_m, from_variable_m):
    """When loading from env_var"""
    config_file_path: Mock = from_variable_m.return_value


    config = config_file_parser.load_config.__wrapped__(env_variable=sentinel.my_variable)

    assert isinstance(config, config_file_parser.Config) is True
    assert config.device_config_data is jsload_m.return_value

    from_variable_m.assert_called_once_with(sentinel.my_variable, config_file_parser.DEFAULT_CONFIG_FILENAME)
    jsload_m.assert_called_once_with(config_file_path.open.return_value.__enter__.return_value)
    config_file_path.open.assert_called_once_with("r")


@patch("coppercomm.config_file_parser._config_file_from_path")
@patch("coppercomm.config_file_parser._config_file_from_variable")
@patch("json.load")
def test_load_config_2(jsload_m, from_variable_m, from_path_m):
    """When loading from path given by user"""
    from_variable_m.return_value = None
    my_path = from_path_m.return_value = MagicMock(name="myPath")


    config = config_file_parser.load_config.__wrapped__(my_path, sentinel.my_name)

    assert isinstance(config, config_file_parser.Config) is True
    assert config.device_config_data is jsload_m.return_value

    jsload_m.assert_called_once_with(my_path.open.return_value.__enter__.return_value)
    my_path.open.assert_called_once_with("r")
    from_path_m.assert_called_once_with(my_path, sentinel.my_name)


@patch("coppercomm.config_file_parser._config_file_from_cwd")
@patch("coppercomm.config_file_parser._config_file_from_path")
@patch("coppercomm.config_file_parser._config_file_from_variable")
@patch("json.load")
def test_load_config_3(jsload_m, from_variable_m, from_path_m, from_cwd_m):
    """When loading from CWD"""
    from_variable_m.return_value = None
    from_path_m.return_value = None
    my_path = from_cwd_m.return_value

    config = config_file_parser.load_config.__wrapped__(my_path, sentinel.my_name)

    assert isinstance(config, config_file_parser.Config) is True
    assert config.device_config_data is jsload_m.return_value

    jsload_m.assert_called_once_with(my_path.open.return_value.__enter__.return_value)
    my_path.open.assert_called_once_with("r")
    from_path_m.assert_called_once_with(my_path, sentinel.my_name)


@patch("coppercomm.config_file_parser._config_file_from_home_dir")
@patch("coppercomm.config_file_parser._config_file_from_cwd")
@patch("coppercomm.config_file_parser._config_file_from_path")
@patch("coppercomm.config_file_parser._config_file_from_variable")
@patch("json.load")
def test_load_config_4(jsload_m, from_variable_m, from_path_m, from_cwd_m, from_home_m):
    """When loading from HOME dir"""
    from_variable_m.return_value = None
    from_path_m.return_value = None
    from_cwd_m.return_value = None
    my_path = from_home_m.return_value

    config = config_file_parser.load_config.__wrapped__(my_path, sentinel.my_name)

    assert isinstance(config, config_file_parser.Config) is True
    assert config.device_config_data is jsload_m.return_value

    jsload_m.assert_called_once_with(my_path.open.return_value.__enter__.return_value)
    my_path.open.assert_called_once_with("r")
    from_path_m.assert_called_once_with(my_path, sentinel.my_name)


@patch("coppercomm.config_file_parser._config_file_from_home_dir")
@patch("coppercomm.config_file_parser._config_file_from_cwd")
@patch("coppercomm.config_file_parser._config_file_from_path")
@patch("coppercomm.config_file_parser._config_file_from_variable")
@patch("json.load")
def test_load_config_5(jsload_m, from_variable_m, from_path_m, from_cwd_m, from_home_m):
    """When config file was not found exception is raised."""
    from_variable_m.return_value = None
    from_path_m.return_value = None
    from_cwd_m.return_value = None
    from_home_m.return_value = None

    with pytest.raises(config_file_parser.ConfigFileParseError):
        config_file_parser.load_config.__wrapped__()
