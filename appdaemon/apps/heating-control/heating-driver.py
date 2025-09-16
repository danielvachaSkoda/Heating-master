import appdaemon.plugins.hass.hassapi as hass


ATTR_SWITCH_HEATING = "switch_heating"
ATTR_ROOMS = "rooms"
HYSTERESIS = 1 # in celsius
ATTR_DEFAULT_MODE = "mode"
MODE_SCHEDULE = "scheduler"
MODE_MANUAL = "manual"
ATTR_SCHEDULER = "scheduler"
ATTR_SENSOR = "thermostats"
ATTR_THERMOSTATS = "thermostats"
HVAC_HEAT = "heat"
HVAC_OFF = "off"

ATTR_CURRENT_TEMP = "current_temperature"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_HVAC_MODES = "hvac_modes"
ATTR_TEMPERATURE = "temperature"
ATTR_TEMPERATURE_DAY = "temperature_day"

#
# Hellow World App
#
# Args:
#

class Heating(hass.Hass):

    def initialize(self):
        self.log("Hello from AppDaemon")
        self.log("You are now ready to run Apps!")
        self.__rooms = self.args.get(ATTR_ROOMS)
        self.__switch_heating = self.args.get(ATTR_SWITCH_HEATING)
        self.__update_thermostats()
        self.init_all_rooms()
        self.run_every(self.run_periodic_rooms, "now", 1 * 30)

    def init_all_rooms(self):
        for room in self.__rooms:
            self.log(f" call init_all_rooms")
            self.listen_state(self.target_changed, room[ATTR_THERMOSTATS])

    def run_periodic_rooms(self, kwargs):
        """This method will be called every 5 minutes"""
        self.log("Running periodic update...", level="INFO")
        heatOnB = False
        for room in self.__rooms:
            self.log(f"mistnost plan:  {room[ATTR_SCHEDULER]} ")
            self.log(f" mode : {room['mode']}")
            demandTemp = self.get_demand_temperature(room['scheduler'])
            self.log(f" demandTemp value: {demandTemp}")
            currTemp=self.get_current_temperature(room[ATTR_THERMOSTATS])
            self.log(f"current Temp Value: {currTemp}")
            if demandTemp>currTemp+HYSTERESIS:
                self.log("Turning heating on.")
                heatOnB=True
        self.__set_heating(heatOnB)

    def __set_heating(self, heat: bool):
        """Set the relay on/off"""
        is_heating = self.is_heating()
        if heat:
            if not is_heating:
                self.log("Turning heating on in set heating")
                self.turn_on(self.__switch_heating)
        else:
            if is_heating:
                self.log("Turning heating off. in set heating")
                self.turn_off(self.__switch_heating)

    def target_changed(self, entity, attribute, old, new, kwargs):
        """Event handler: target temperature"""
        self.log(" called target_changed")
        self.__update_heating()
        for room in self.__rooms:
            if (
                    room[ATTR_TEMPERATURE_DAY] == entity
                    or room[ATTR_TEMPERATURE_NIGHT] == entity
            ):
                self.__update_thermostats(sensor_entity=room[ATTR_THERMOSTATS])

    def is_heating(self) -> bool:
        return bool(self.get_state(self.__switch_heating).lower() == "on")

    def get_demand_temperature(self,entity_scheduler) -> float:
        attributes = self.get_state(entity_scheduler, attribute="all")
        temperature = attributes["attributes"].get("temperature")
        return float(temperature)

    def get_current_temperature(self,entity_thermostat) -> float:
        attributesT = self.get_state(entity_thermostat, attribute="all")
        self.log(f"Turning heating on in set heating {attributesT}")
        currentTempValue = attributesT["attributes"].get('current_temperature')
        return float(currentTempValue)


    def __get_target_room_temp(self, room) -> float:
        """Returns target room temparture, based on day/night switch (not considering vacation)"""
        #if bool(self.get_state(room[ATTR_DAYNIGHT]).lower() == "on"):
        #    return float(self.get_state(room[ATTR_TEMPERATURE_DAY]))
        #else:
        #    return float(self.get_state(room[ATTR_TEMPERATURE_NIGHT]))
        attributes = self.get_state(room[MODE_SCHEDULE], attribute="all")
        temperature = attributes["attributes"].get("temperature")
        return float(temperature)

    def __set_thermostat(
            self, entity_id: str, target_temp: float, current_temp: float, mode: str
    ):
        """Set the thermostat attrubutes and state"""
        if target_temp is None:
            target_temp = self.__get_target_temp(termostat=entity_id)
        if current_temp is None:
            current_temp = self.__get_current_temp(termostat=entity_id)
        if mode is None:
            if self.is_heating():
                mode = HVAC_HEAT
            else:
                mode = HVAC_OFF
        self.log(
            f"Updating thermostat {entity_id}: "
            f"temperature target {target_temp}, "
            f"mode {mode}, "
            f"current temperature {current_temp}.")
        if current_temp is not None and target_temp is not None and mode is not None:
            attrs = {}
            attrs[ATTR_CURRENT_TEMP] = current_temp
            attrs[ATTR_TEMPERATURE] = target_temp
            attrs[ATTR_HVAC_MODE] = mode
            attrs[ATTR_HVAC_MODES] = [HVAC_HEAT, HVAC_OFF]
            self.set_state(entity_id, state=mode, attributes=attrs)
            self.call_service(
                "climate/set_temperature", entity_id=entity_id, temperature=target_temp
            )
            self.log(f" call set atribute ok {attrs}")



    def __update_thermostats(self, thermostat_entity: str = None):
        """Set the thermostats target temperature, current temperature and heating mode"""
        #vacation = self.get_mode() == MODE_VACATION
        #vacation_temperature = float(self.get_state(self.__temperature_vacation))

        for room in self.__rooms:
            if (
                    (thermostat_entity is None)
                    or (thermostat_entity in room[ATTR_THERMOSTATS])
            ):
                self.log(f"updating sensor {room[ATTR_THERMOSTATS]}")
                temperature = self.get_current_temperature(room[ATTR_THERMOSTATS])
                self.log(f" temperature {temperature}")
                target_temperature = self.__get_target_room_temp(room)
                self.log(f" target_temperature {target_temperature}")
                if self.is_heating():
                    mode = HVAC_HEAT
                else:
                    mode = HVAC_OFF
                self.log(f"in room thermostat: {room[ATTR_THERMOSTATS]}")
                self.__set_thermostat(room[ATTR_THERMOSTATS], target_temperature, temperature, mode)



