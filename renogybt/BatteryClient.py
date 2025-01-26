from .BaseClient import BaseClient
from .Utils import bytes_to_int, format_temperature

# Client for Renogy LFP battery with built-in bluetooth / BT-2 module

FUNCTION = {3: "READ", 6: "WRITE"}


class BatteryClient(BaseClient):
    def __init__(self, config, on_data_callback=None, on_error_callback=None):
        super().__init__(config)
        self.on_data_callback = on_data_callback
        self.on_error_callback = on_error_callback
        self.data = {}
        self.sections = [
            {"register": 5000, "words": 17, "parser": self.parse_cell_volt_info},
            {"register": 5017, "words": 17, "parser": self.parse_cell_temp_info},
            {"register": 5035, "words": 7, "parser": self.parse_battery_env_info},
            {"register": 5042, "words": 6, "parser": self.parse_battery_info},
            {"register": 5048, "words": 5, "parser": self.parse_limits_info},
            {"register": 5048, "words": 5, "parser": self.parse_limits_info},
            {"register": 5100, "words": 10, "parser": self.parse_alarm_info},
            # {"register": 5110, "words": 8, "parser": self.parse_sn},
            {"register": 5118, "words": 1, "parser": self.parse_man_ver},
            {"register": 5119, "words": 2, "parser": self.parse_main_ver},
            {"register": 5121, "words": 1, "parser": self.parse_comms_ver},
            {"register": 5122, "words": 8, "parser": self.parse_name},
            {"register": 5130, "words": 2, "parser": self.parse_sw_ver},
            {"register": 5132, "words": 10, "parser": self.parse_manufacturer},
            {"register": 5223, "words": 1, "parser": self.parse_device_address},
            {"register": 5226, "words": 2, "parser": self.parse_unique_id},
            {"register": 5228, "words": 1, "parser": self.parse_charge_power},
            {"register": 5229, "words": 1, "parser": self.parse_discharge_power},
        ]

    def parse_cell_volt_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["cell_count"] = bytes_to_int(bs, 3, 2)
        for i in range(0, data["cell_count"]):
            data[f"cell_voltage_{i}"] = bytes_to_int(bs, 5 + i * 2, 2, scale=0.1)
        self.data.update(data)

    def parse_cell_temp_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["sensor_count"] = bytes_to_int(bs, 3, 2)
        for i in range(0, data["sensor_count"]):
            celcius = bytes_to_int(bs, 5 + i * 2, 2, scale=0.1, signed=True)
            data[f"temperature_{i}"] = format_temperature(
                celcius, self.config["data"]["temperature_unit"]
            )
        self.data.update(data)

    def parse_battery_env_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["bms_board_temp"] = format_temperature(
            bytes_to_int(bs, 3, 2, scale=0.1, signed=True),
            self.config["data"]["temperature_unit"],
        )
        data["env_temp_count"] = bytes_to_int(bs, 5, 2)
        data["env_temp_1"] = format_temperature(
            bytes_to_int(bs, 7, 2, scale=0.1), self.config["data"]["temperature_unit"]
        )
        data["env_temp_2"] = format_temperature(
            bytes_to_int(bs, 9, 2, scale=0.1), self.config["data"]["temperature_unit"]
        )
        data["heater_temp_count"] = bytes_to_int(bs, 11, 2)
        data["heater_temp_1"] = format_temperature(
            bytes_to_int(bs, 13, 2, scale=0.1), self.config["data"]["temperature_unit"]
        )
        data["heater_temp_2"] = format_temperature(
            bytes_to_int(bs, 15, 2, scale=0.1), self.config["data"]["temperature_unit"]
        )
        self.data.update(data)

    def parse_battery_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["current"] = bytes_to_int(bs, 3, 2, True, scale=0.01)
        data["voltage"] = bytes_to_int(bs, 5, 2, scale=0.1)
        data["remaining_charge"] = bytes_to_int(bs, 7, 4, scale=0.001)
        data["capacity"] = bytes_to_int(bs, 11, 4, scale=0.001)
        self.data.update(data)

    def parse_limits_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["cycle_count"] = bytes_to_int(bs, 3, 2)
        data["charge_voltage_limit"] = bytes_to_int(bs, 5, 2, scale=0.1)
        data["discharge_voltage_limit"] = bytes_to_int(bs, 7, 2, scale=0.1)
        data["charge_current_limit"] = bytes_to_int(bs, 9, 2, scale=0.01)
        data["discharge_current_limit"] = bytes_to_int(bs, 11, 2, True, scale=0.01)
        self.data.update(data)

    def parse_alarm_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["cell_voltage_alarm"] = bytes_to_int(bs, 3, 4)
        # need to do this for all 16 cells
        data["cell_temperature_alarm"] = bytes_to_int(bs, 7, 4)
        # need to do this for all 16 cells
        data["other_alarm"] = bytes_to_int(bs, 11, 4)
        data["status_1"] = bytes_to_int(bs, 15, 2)
        data["status_1_values"] = {
            "module_under_voltage": (data["status_1"] & 0x8000) >> 15,
            "charge_over_temp": (data["status_1"] & 0x4000) >> 14,
            "charge_under_temp": (data["status_1"] & 0x2000) >> 13,
            "discharge_over_temp": (data["status_1"] & 0x1000) >> 12,
            "discharge_under_temp": (data["status_1"] & 0x0800) >> 11,
            "discharge_over_current1": (data["status_1"] & 0x0400) >> 10,
            "charge_over_current1": (data["status_1"] & 0x0200) >> 9,
            "cell_over_voltage": (data["status_1"] & 0x0100) >> 8,
            "cell_under_voltage": (data["status_1"] & 0x0080) >> 7,
            "module_over_voltage": (data["status_1"] & 0x0040) >> 6,
            "discharge_over_current2": (data["status_1"] & 0x0020) >> 5,
            "charge_over_current2": (data["status_1"] & 0x0010) >> 4,
            "using_battery_module_power": (data["status_1"] & 0x0008) >> 3,
            "discharge_MOSFET": (data["status_1"] & 0x0004) >> 2,
            "charge_MOSFET": (data["status_1"] & 0x0002) >> 1,
            "short_circuit": (data["status_1"] & 0x0001) >> 0,
        }
        data["status_2"] = bytes_to_int(bs, 17, 2)
        data["status_2_values"] = {
            "effective_charge_current": (data["status_2"] & 0x8000) >> 15,
            "effective_discharge_current": (data["status_2"] & 0x4000) >> 14,
            "heater_on": (data["status_2"] & 0x2000) >> 13,
            "reserved": (data["status_2"] & 0x1000) >> 12,
            "fully_charged": (data["status_2"] & 0x0800) >> 11,
            "reserved_10": (data["status_2"] & 0x0400) >> 10,
            "reserved_09": (data["status_2"] & 0x0200) >> 9,
            "buzzer": (data["status_2"] & 0x0100) >> 8,
            "discharge_high_temp": (data["status_2"] & 0x0080) >> 7,
            "discharge_low_temp": (data["status_2"] & 0x0040) >> 6,
            "charge_high_temp": (data["status_2"] & 0x0020) >> 5,
            "charge_low_temp": (data["status_2"] & 0x0010) >> 4,
            "module_high_voltage": (data["status_2"] & 0x0008) >> 3,
            "module_low_voltage": (data["status_2"] & 0x0004) >> 2,
            "cell_high_voltage": (data["status_2"] & 0x0002) >> 1,
            "cell_low_voltage": (data["status_2"] & 0x0001) >> 0,
        }
        data["status_3"] = bytes_to_int(bs, 19, 2)
        data["status_3_values"] = {
            "cell_16_voltage": (data["status_3"] & 0x8000) >> 15,
            "cell_15_voltage": (data["status_3"] & 0x4000) >> 14,
            "cell_14_voltage": (data["status_3"] & 0x2000) >> 13,
            "cell_13_voltage": (data["status_3"] & 0x1000) >> 12,
            "cell_12_voltage": (data["status_3"] & 0x0800) >> 11,
            "cell_11_voltage": (data["status_3"] & 0x0400) >> 10,
            "cell_10_voltage": (data["status_3"] & 0x0200) >> 9,
            "cell_9_voltage": (data["status_3"] & 0x0100) >> 8,
            "cell_8_voltage": (data["status_3"] & 0x0080) >> 7,
            "cell_7_voltage": (data["status_3"] & 0x0040) >> 6,
            "cell_6_voltage": (data["status_3"] & 0x0020) >> 5,
            "cell_5_voltage": (data["status_3"] & 0x0010) >> 4,
            "cell_4_voltage": (data["status_3"] & 0x0008) >> 3,
            "cell_3_voltage": (data["status_3"] & 0x0004) >> 2,
            "cell_2_voltage": (data["status_3"] & 0x0002) >> 1,
            "cell_1_voltage": (data["status_3"] & 0x0001) >> 0,
        }
        data["charge_discharge_status"] = bytes_to_int(bs, 21, 2)
        data["charge_discharge_status_values"] = {
            "charge_enable": (data["charge_discharge_status"] & 0x0080) >> 7,
            "discharge_enable": (data["charge_discharge_status"] & 0x0040) >> 6,
            "charge_immediately1": (data["charge_discharge_status"] & 0x0020) >> 5,
            "charge_immediately2": (data["charge_discharge_status"] & 0x0010) >> 4,
            "full_charge": (data["charge_discharge_status"] & 0x0008) >> 3,
            "reserved_2": (data["charge_discharge_status"] & 0x0004) >> 2,
            "reserved_1": (data["charge_discharge_status"] & 0x0002) >> 1,
            "reserved_0": (data["charge_discharge_status"] & 0x0001) >> 0,
        }

        self.data.update(data)

    def parse_misc_info(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        #  data["serial_number"] = (bs[3:19]).decode("utf-8").rstrip("\x00")
        data["manufacture_version"] = (bs[20:22]).decode("utf-8").rstrip("\x00")
        data["main_line_version"] = (bs[23:27]).decode("utf-8").rstrip("\x00")
        data["communication_protocol_version"] = (bs[28:30]).decode("utf-8").rstrip("\x00")
        data["battery_name"] = (bs[31:47]).decode("utf-8").rstrip("\x00")
        data["software_version"] = (bs[48:52]).decode("utf-8").rstrip("\x00")
        data["manufacturer_name"] = (bs[53:73]).decode("utf-8").rstrip("\x00")
        self.data.update(data)

    def parse_sn(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["serial_number"] = (bs[3:19]).decode("ISO-8859-1")
        self.data.update(data)

    def parse_man_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["manufacture_version"] = (bs[3:5]).decode("utf-8")
        self.data.update(data)

    def parse_main_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["main_line_version"] = (bs[3:7]).decode("utf-8")
        self.data.update(data)

    def parse_comms_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["communication_protocol_version"] = (bs[3:5]).decode("utf-8")
        self.data.update(data)

    def parse_name(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["battery_name"] = (bs[3:19]).decode("utf-8").rstrip("\x00")
        self.data.update(data)

    def parse_sw_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["software_version"] = (bs[3:5]).decode("utf-8")
        self.data.update(data)

    def parse_manufacturer(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["manufacturer_name"] = (bs[3:23]).decode("utf-8").rstrip("\x00")
        self.data.update(data)

    def parse_device_address(self, bs):
        data = {}
        data["device_id"] = bytes_to_int(bs, 3, 2)
        self.data.update(data)

    def parse_unique_id(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["unique_id"] = bytes_to_int(bs, 3, 4)
        self.data.update(data)

    def parse_charge_power(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["charge_power_percent"] = bytes_to_int(bs, 3, 2)
        self.data.update(data)

    def parse_discharge_power(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["discharge_power_percent"] = bytes_to_int(bs, 3, 2)
        self.data.update(data)
