from .BaseClient import BaseClient
from .Utils import bytes_to_int, format_temperature
import logging
from struct import unpack_from

# Client for Renogy LFP battery with built-in bluetooth / BT-2 module

FUNCTION = {3: "READ", 6: "WRITE"}

ALARMS = {0: "none", 1: "below", 2: "above", 3: "other"}
PROTECTION = {0: "normal", 1: "trigger"}
WARNING = {0: "normal", 1: "trigger"}
USING = {0: "not", 1: "using"}
STATE = {0: "off", 1: "on"}
CHARGED_STATE = {0: "normal", 1: "full"}
EFFECTIVE_STATE = {0: "normal", 1: "effective"}
ERROR_STATE = {0: "normal", 1: "error"}
ERROR_STATE = {0: "normal", 1: "error"}
CHARGE_REQUEST = {0: "normal", 1: "yes"}
CHARGE_ENABLE_REQUEST = {0: "normal", 1: "requestStopCharge"}
DISCHARGE_ENABLE_REQUEST = {0: "normal", 1: "requestStopDischarge"}


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
            {"register": 5100, "words": 10, "parser": self.parse_alarm_info},
            {"register": 5110, "words": 8, "parser": self.parse_sn},
            {"register": 5118, "words": 1, "parser": self.parse_man_ver},
            {"register": 5119, "words": 2, "parser": self.parse_main_ver},
            {"register": 5121, "words": 1, "parser": self.parse_comms_ver},
            {"register": 5122, "words": 8, "parser": self.parse_name},
            {"register": 5130, "words": 2, "parser": self.parse_sw_ver},
            {"register": 5132, "words": 10, "parser": self.parse_manufacturer},
            {"register": 5200, "words": 21, "parser": self.parse_device_configuration_1},
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
        data["environment_temperature_count"] = bytes_to_int(bs, 5, 2)
        for i in range(0, data["environment_temperature_count"]):
            data[f"environment_temperature_{i}"] = format_temperature(
                bytes_to_int(bs, 7 + i * 2, 2, scale=0.1, signed=True),
                self.config["data"]["temperature_unit"],
            )
        data["heater_temperature_count"] = bytes_to_int(bs, 11, 2)
        for i in range(0, data["heater_temperature_count"]):
            data[f"heater_temperature_{i}"] = format_temperature(
                bytes_to_int(bs, 13 + i * 2, 2, scale=0.1, signed=True),
                self.config["data"]["temperature_unit"],
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
        cell_voltage_alarms = bytes_to_int(bs, 3, 4)
        cell_temperature_alarms = bytes_to_int(bs, 7, 4)
        data["cell_voltage_alarm"] = cell_voltage_alarms
        data["cell_temperature_alarm"] = cell_temperature_alarms

        for i in range(0, self.data["cell_count"]):
            data[f"cell_voltage_alarm_{i}"] = ALARMS[cell_voltage_alarms & 3]
            data[f"cell_temperature_alarm_{i}"] = ALARMS[cell_temperature_alarms & 3]
            cell_voltage_alarms = cell_voltage_alarms >> 2
            cell_temperature_alarms = cell_temperature_alarms >> 2

        alarms = bytes_to_int(bs, 11, 4)
        data["other_alarm"] = alarms
        alarms = alarms >> 18  # first 18 bits are reserved
        data["discharge_current_alarm"] = ALARMS[alarms & 3]
        alarms = alarms >> 2
        data["charge_current_alarm"] = ALARMS[alarms & 3]
        alarms = alarms >> 2
        data["heater_temperature_2_alarm"] = ALARMS[alarms & 3]
        alarms = alarms >> 2
        data["heater_temperature_1_alarm"] = ALARMS[alarms & 3]
        alarms = alarms >> 2
        data["env_temperature_2_alarm"] = ALARMS[alarms & 3]
        alarms = alarms >> 2
        data["env_temperature_1_alarm"] = ALARMS[alarms & 3]
        alarms = alarms >> 2
        data["bms_board_temperature_alarm"] = ALARMS[alarms & 3]

        status_1 = bytes_to_int(bs, 15, 2)
        data["status_1"] = status_1
        data["short_circuit"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["charge_MOSFET"] = STATE[status_1 & 1]
        status_1 = status_1 >> 1
        data["discharge_MOSFET"] = STATE[status_1 & 1]
        status_1 = status_1 >> 1
        data["using_battery_module_power"] = USING[status_1 & 1]
        status_1 = status_1 >> 1
        data["charge_over_current_2"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["discharge_over_current_2"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["module_over_voltage"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["cell_under_voltage"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["cell_over_voltage"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["charge_over_current_1"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["discharge_over_current_1"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["discharge_under_temp"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["discharge_over_temp"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["charge_under_temp"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["charge_over_temp"] = PROTECTION[status_1 & 1]
        status_1 = status_1 >> 1
        data["module_under_voltage"] = PROTECTION[status_1 & 1]

        status_2 = bytes_to_int(bs, 17, 2)
        data["status_2"] = status_2
        data["cell_low_voltage"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["cell_high_voltage"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["module_low_voltage"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["module_high_voltage"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["charge_low_temp"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["charge_high_temp"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["discharge_low_temp"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["discharge_high_temp"] = WARNING[status_2 & 1]
        status_2 = status_2 >> 1
        data["buzzer"] = STATE[status_2 & 1]
        status_2 = status_2 >> 3
        data["fully_charged"] = CHARGED_STATE[status_2 & 1]
        status_2 = status_2 >> 2
        data["heater_on"] = STATE[status_2 & 1]
        status_2 = status_2 >> 1
        data["effective_discharge_current"] = EFFECTIVE_STATE[status_2 & 1]
        status_2 = status_2 >> 1
        data["effective_charge_current"] = EFFECTIVE_STATE[status_2 & 1]

        status_3 = bytes_to_int(bs, 19, 2)
        data["status_3"] = status_3

        for i in range(0, self.data["cell_count"]):
            data[f"cell_voltage_error_state_{i}"] = ERROR_STATE[status_3 & 1]
            status_3 = status_3 >> 1

        charge_discharge_status = bytes_to_int(bs, 21, 2)
        data["charge_discharge_status"] = charge_discharge_status
        charge_discharge_status = charge_discharge_status >> 3  # first 3 bits are reserved
        data["full_charge_request"] = CHARGE_REQUEST[charge_discharge_status & 1]
        charge_discharge_status = charge_discharge_status >> 1
        data["charge_immediately_1"] = CHARGE_REQUEST[charge_discharge_status & 1]
        charge_discharge_status = charge_discharge_status >> 1
        data["charge_immediately_2"] = CHARGE_REQUEST[charge_discharge_status & 1]
        charge_discharge_status = charge_discharge_status >> 1
        data["discharge_enable"] = DISCHARGE_ENABLE_REQUEST[charge_discharge_status & 1]
        charge_discharge_status = charge_discharge_status >> 1
        data["charge_enable"] = CHARGE_ENABLE_REQUEST[charge_discharge_status & 1]

        self.data.update(data)

    def parse_sn(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))

        bytesVar = bs[3:19]
        try:
            data["serial_number"] = bytesVar.decode("ascii").rstrip("\x00")
        except UnicodeDecodeError as e:
            logging.exception("Failed to decode serial number", e)
            data["serial_number"] = bytesVar.hex()

        self.data.update(data)

    def parse_man_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["manufacture_version"] = (bs[3:5]).decode("utf-8")
        self.data.update(data)

    def parse_main_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        version = bs[3:7]
        version_major, version_minor = unpack_from("2s2s", version)
        version_major = version_major.decode("utf-8")
        version_minor = version_minor.decode("utf-8")
        data["main_line_version"] = float(f"{version_major}.{version_minor}")
        self.data.update(data)

    def parse_comms_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["communication_protocol_version"] = (bs[3:5]).decode("utf-8")
        self.data.update(data)

    def parse_name(self, bs):
        data = {}
        data["device"] = bytes_to_int(bs, 0, 1)
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["battery_name"] = (bs[3:19]).decode("utf-8").rstrip("\x00")
        self.data.update(data)

    def parse_sw_ver(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        version = bs[3:7]
        version_major, version_minor = unpack_from("2s2s", version)
        version_major = version_major.decode("utf-8")
        version_minor = version_minor.decode("utf-8")
        data["software_version"] = float(f"{version_major}.{version_minor}")
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

    def parse_device_configuration_1(self, bs):
        data = {}
        data["function"] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data["config_cell_over_voltage_limit"] = bytes_to_int(bs, 3, 2, scale=0.1)
        data["config_cell_high_voltage_limit"] = bytes_to_int(bs, 5, 2, scale=0.1)
        data["config_cell_low_voltage_limit"] = bytes_to_int(bs, 7, 2, scale=0.1)
        data["config_cell_under_voltage_limit"] = bytes_to_int(bs, 9, 2, scale=0.1)
        data["config_charge_over_temp_limit"] = bytes_to_int(bs, 11, 2, scale=0.1)
        data["config_charge_high_temp_limit"] = bytes_to_int(bs, 13, 2, scale=0.1)
        data["config_charge_low_temp_limit"] = bytes_to_int(bs, 15, 2, scale=0.1)
        data["config_charge_under_temp_limit"] = bytes_to_int(bs, 17, 2, scale=0.1)
        data["config_charge_over2_current_limit"] = bytes_to_int(bs, 19, 2, scale=0.01)
        data["config_charge_over_current_limit"] = bytes_to_int(bs, 21, 2, scale=0.01)
        data["config_charge_high_current_limit"] = bytes_to_int(bs, 23, 2, scale=0.01)
        data["config_module_over_voltage_limit"] = bytes_to_int(bs, 25, 2, scale=0.1)
        data["config_module_high_voltage_limit"] = bytes_to_int(bs, 27, 2, scale=0.1)
        data["config_module_low_voltage_limit"] = bytes_to_int(bs, 29, 2, scale=0.1)
        data["config_module_under_voltage_limit"] = bytes_to_int(bs, 31, 2, scale=0.1)
        data["config_discharge_over_temp_limit"] = bytes_to_int(bs, 33, 2, scale=0.1)
        data["config_discharge_high_temp_limit"] = bytes_to_int(bs, 35, 2, scale=0.1)
        data["config_discharge_low_temp_limit"] = bytes_to_int(bs, 37, 2, scale=0.1, signed=True)
        data["config_discharge_under_temp_limit"] = bytes_to_int(bs, 39, 2, scale=0.1, signed=True)
        data["config_discharge_over2_current_limit"] = bytes_to_int(
            bs, 41, 2, scale=0.01, signed=True
        )
        data["config_discharge_over_current_limit"] = bytes_to_int(
            bs, 43, 2, scale=0.01, signed=True
        )
        data["config_discharge_high_current_limit"] = bytes_to_int(
            bs, 45, 2, scale=0.01, signed=True
        )
        self.data.update(data)
