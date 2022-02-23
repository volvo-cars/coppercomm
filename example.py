from test_manager.devices.ci_config import Config

def create_dut():
    """Create the device object based on the Config"""
    test = Config
    test_device = test.load_device()

    with test_device.managed as device:
        yield device

def test_dut():
    dut = create_dut()
    dut.adb.shell("getprop")

if __name__ == "__main__":
    """Run the example"""
    dut = create_dut()
