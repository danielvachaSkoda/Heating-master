import math
import time
import appdaemon.plugins.hass.hassapi as hass

## todo  prepare bool function is any entity in switching state

ATTR_SWITCH_HEATING = "switch_heating"
ATTR_ROOMS = "rooms"
HYSTERESIS = 1 # in celsius
ATTR_DEFAULT_MODE = "mode"

# 2 type of room mode
MODE_SCHEDULE = "scheduler"
MODE_MANUAL = "manual"

# 2 type of state
STATE_SWITCHING = "switching" # actual switching do not response to changes in  thermostat
STATE_NORMAL = "normal"

ATTR_SCHEDULER = "scheduler"
ATTR_SENSOR = "thermostat"
ATTR_THERMOSTATS = "thermostat"

# 2 types of boiler mode
HVAC_HEAT = "heat"
HVAC_OFF = "off"

ATTR_CURRENT_TEMP = "current_temperature"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_HVAC_MODES = "hvac_modes"
ATTR_TEMPERATURE = "temperature"
ATTR_TEMPERATURE_DAY = "temperature_day"
ATTR_ENTITY_ID = "entity_id"

# partial name for schedule entity
ATTR_SCHEDULE = "schedule"

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
        self.__room_mode_dict={}
        self.__entity_state_dict={}
        self.__switch_heating = self.args.get(ATTR_SWITCH_HEATING)
        self.init_all_rooms()
        self.__update_thermostats()
        #self.run_every(self.run_periodic_rooms, "now", 1 * 20)

    def init_all_rooms(self):
        for room in self.__rooms:
            entity_climate=room[ATTR_THERMOSTATS]
            self.setMode(MODE_SCHEDULE,entity_climate)
            self.log(f" call init_all_rooms: {entity_climate}")
            self.get_attributes(room)
            self.handle = self.listen_state(self.target_changed,entity_climate,attribute="temperature")
            entity_scheduler=room[ATTR_SCHEDULER]
            self.log(f" call init_all_rooms: {entity_scheduler}")
            self.setMode(MODE_SCHEDULE,entity_climate)
            self.handle = self.listen_state(self.target_changed,entity_scheduler,attribute="temperature")

    def setMode(self,mode,entity_climate):
        attributes = self.get_state(entity_climate, attribute="all")
        climate_id = attributes[ATTR_ENTITY_ID]
        self.log(f" climate_id: {climate_id}")
        self.__room_mode_dict[climate_id]=mode

    def getMode(self,room) -> str:
        entity_climate=room[ATTR_THERMOSTATS]
        attributes = self.get_state(entity_climate, attribute="all")
        climate_id = attributes[ATTR_ENTITY_ID]
        self.log(f"getMode -for {climate_id}", level="INFO")
        return self.__room_mode_dict[climate_id]

    def getEntityState(self,entity) -> str:
        attributes = self.get_state(entity, attribute="all")
        climate_id = attributes[ATTR_ENTITY_ID]
        self.log(f"getMode -for {climate_id}", level="INFO")
        return self.__entity_state_dict[climate_id]

    def setEntityState(self,state,entity):
        attributes = self.get_state(entity, attribute="all")
        climate_id = attributes[ATTR_ENTITY_ID]
        self.log(f" entity_id: {climate_id}")
        self.__entity_state_dict[climate_id]=state

    def getModeByEntity(self,entity_climate) -> str:
        attributes = self.get_state(entity_climate, attribute="all")
        climate_id = attributes[ATTR_ENTITY_ID]
        return self.__room_mode_dict[climate_id]

    def run_periodic_rooms(self, kwargs):
        """This method will be called every 5 minutes"""
        self.log("", level="INFO")
        self.log("Running periodic update...", level="INFO")
        self.log(f" self.__room_mode_dict  {self.__room_mode_dict}")
        heatOnB = False
        for room in self.__rooms:
            self.log(f"mistnost plan:  {room[ATTR_SCHEDULER]} ")
            room_mode=self.getMode(room)
            self.log(f" room_mode : {room_mode}")
            demandTemp = self.get_demand_temperature_by_mode(room_mode,room)
            self.log(f" demandTemp value: {demandTemp}")
            currTemp=self.get_current_temperature(room[ATTR_THERMOSTATS])
            self.log(f"current Temp Value: {currTemp}")
            mode= self.getMode(room)
            self.log(f"current modee: {mode}")
            if demandTemp>currTemp+HYSTERESIS:
                self.log("Turning heating on.")
                heatOnB=True
        self.__set_heating(heatOnB)

    def infoClimate(self,room):
        entity_climate=room[ATTR_THERMOSTATS]
        self.infoClimateEntity(entity_climate)

    def infoClimateEntity(self,entity_climate):
        attributes = self.get_state(entity_climate, attribute="all")
        self.log(f"infoClimateEntity: {attributes}")
        modeDict=self.__room_mode_dict[entity_climate]
        self.log(f"modeDict: {modeDict}")

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
        self.log(f" entity: {entity}")
        self.log(f" attribute: {attribute}")
        self.log(f" old: {old}")
        self.log(f" new: {new}")
        bbb = ATTR_SCHEDULE in entity
        self.log(f" ATTR_SCHEDULE in ent : {bbb}")
        if ATTR_SCHEDULE in entity:
            self.setEntityState(STATE_SWITCHING,entity)
            self.setMode(MODE_SCHEDULE,entity)
            self.__update_thermostats(scheduler_entity=entity)
        elif self.getEntityState(entity) != STATE_SWITCHING:
            self.setMode(MODE_MANUAL,entity)
            self.__update_thermostats(thermostat_entity=entity)

    def is_heating(self) -> bool:
        return bool(self.get_state(self.__switch_heating).lower() == "on")

    def get_demand_temperature(self,entity) -> float:
        """Return demand temperature  from entity climate, or schedule(alsou return math.nan)"""
        attributes = self.get_state(entity, attribute="all")
        temperature = attributes["attributes"].get("temperature")
        if temperature == 'None':
            return math.nan
        return float(temperature)

    def get_demand_temperature_by_mode(self,room_mode,room) -> float:
        if room_mode.lower() == MODE_SCHEDULE.lower():
            return self.get_demand_temperature(room[ATTR_SCHEDULER])
        if room_mode.lower() == MODE_MANUAL.lower():
            return self.get_demand_temperature(room[ATTR_THERMOSTATS])

    def get_attributes(self,room):
        entity=room[ATTR_SCHEDULER]
        attributes = self.get_state(entity, attribute="all")
        self.log(f" call get_attributes {attributes}")

    def get_current_temperature(self,entity_thermostat) -> float:
        attributesT = self.get_state(entity_thermostat, attribute="all")
        currentTempValue = attributesT["attributes"].get('current_temperature')
        return float(currentTempValue)

    def __set_thermostat(
            self, entity_id: str, target_temp: float, current_temp: float, boiler_mode: str
    ):
        """Set the thermostat attrubutes and state"""
        if target_temp is None:
            target_temp = self.__get_target_temp(termostat=entity_id)
        if current_temp is None:
            current_temp = self.__get_current_temp(termostat=entity_id)
        if boiler_mode is None:
            boiler_mode=self.get_boilerMode()
        self.log(
            f"Updating thermostat {entity_id}: "
            f"temperature target {target_temp}, "
            f"mode {boiler_mode}, "
            f"current temperature {current_temp}.")
        if current_temp is not None and target_temp is not None and boiler_mode is not None:
            attrs = {}
            attrs[ATTR_CURRENT_TEMP] = current_temp
            attrs[ATTR_TEMPERATURE] = target_temp
            attrs[ATTR_HVAC_MODE] = boiler_mode
            attrs['preset_mode'] = 'Schedule'
            attrs[ATTR_HVAC_MODES] = [HVAC_HEAT, HVAC_OFF]
            self.set_state(entity_id, state='Schedule', attributes=attrs)
            self.call_service(
                "climate/set_temperature", entity_id=entity_id, temperature=target_temp
            )
            self.log(f" call set atribute ok {attrs}")

    def get_boilerMode(self) -> str:
        if self.is_heating():
            return HVAC_HEAT
        else:
            return HVAC_OFF

    def __update_thermostats(self, thermostat_entity: str = None, scheduler_entity: str = None):
        """Set the thermostats target temperature, current temperature and heating mode"""
        #vacation = self.get_mode() == MODE_VACATION
        #vacation_tempself.log(f" room_mode {temperature}")erature = float(self.get_state(self.__temperature_vacation))
        self.log(f" __update_thermostats start ")
        for room in self.__rooms:
            self.log(f"updating room with thermostat {room[ATTR_THERMOSTATS]}")
            room_mode=self.getMode(room)
            self.log(f" room_mode {room_mode}")
            temperature = self.get_current_temperature(room[ATTR_THERMOSTATS])
            self.log(f" temperature {temperature}")
            demandTemp = self.get_demand_temperature_by_mode(room_mode,room)
            self.log(f" target_temperature {demandTemp}")
            boiler_mode = self.get_boilerMode()
            self.log(f"in room thermostat: {room[ATTR_THERMOSTATS]}")
            self.__set_thermostat(room[ATTR_THERMOSTATS], demandTemp, temperature, boiler_mode)
            time.sleep(5)
            self.setEntityState(STATE_NORMAL,room[ATTR_SCHEDULER])




