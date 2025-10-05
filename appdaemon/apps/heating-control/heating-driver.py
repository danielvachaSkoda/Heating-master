import math
from datetime import datetime, timedelta
import appdaemon.plugins.hass.hassapi as hass


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
ATTR_ROOM_ID = "room_id"

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
        self.log("You are now ready to Heating!")
        self.__rooms = self.args.get(ATTR_ROOMS)
        self.log(f"rooms {self.__rooms}")
        self.lastSwitchDt=datetime.now()
        self.__room_mode_dict={}
        self.__switch_heating = self.args.get(ATTR_SWITCH_HEATING)
        self.log(f"__switch_heating {self.__switch_heating}")
        self.init_all_rooms()
        self.run_every(self.run_periodic_rooms, "now", 22 * 60)

    def run_periodic_rooms(self, kwargs):
        """This method will be called every 5 minutes"""
        self.log("", level="INFO")
        #self.log("Running periodic update...", level="INFO")
        heatOnB = False
        #history=self.get_history()
        #self.log(f" history  {history}")
        self.get_attributes_shelly()
        for room in self.__rooms:
            room_mode=self.getMode(room)
            temperature = self.get_current_temperature(room[ATTR_THERMOSTATS])
            follow=self.get_follow_state(room[ATTR_SCHEDULER])
            self.log(f"follow {follow}, room_mode {room_mode}, temperature {temperature}")
            demandTemp = self.get_demand_temperature_by_mode(room_mode,room)
            bol=demandTemp>temperature+HYSTERESIS
            self.log(f"run_periodic_rooms Turning ? bol:{bol}")
            if follow and bol:
                self.log(f"run_periodic_rooms Turning heating on. {room[ATTR_ROOM_ID]}")
                heatOnB=True
        if heatOnB:
            self.log("run_periodic_rooms heatOnB true")
            delay_seconds = 1200
            self.__set_heating(heatOnB)
            self.run_in(self.delayed_set_heating, delay_seconds,heat=False)


    def init_all_rooms(self):
        for room in self.__rooms:
            entity_climate=room[ATTR_THERMOSTATS]
            self.log(f" call init_all_rooms: {entity_climate}")
            self.get_attributes(room)
            self.handle = self.listen_state(self.target_changed,entity_climate,attribute="current_temperature")
            self.handle = self.listen_state(self.target_current_temp_changed,entity_climate,attribute="temperature")
            entity_scheduler=room[ATTR_SCHEDULER]
            self.log(f" call init_all_rooms: {entity_scheduler}")
            roomId=room[ATTR_ROOM_ID]
            self.setMode(MODE_SCHEDULE,roomId)
            self.handle = self.listen_state(self.scheduler_changed_temperature,entity_scheduler,attribute="temperature")
            self.__update_thermostat(room)

    def setMode(self,mode,room_id):
        self.log(f"called setMode() room_id: {room_id} set mode {mode}")
        self.__room_mode_dict[room_id]=mode

    def getMode(self,room) -> str:
        room_id=room[ATTR_ROOM_ID]
        #self.log(f"getMode -for {room_id}", level="INFO")
        return self.__room_mode_dict[room_id]

    def getModeByEntity(self,entity_climate) -> str:
        attributes = self.get_state(entity_climate, attribute="all")
        climate_id = attributes[ATTR_ENTITY_ID]
        return self.__room_mode_dict[climate_id]

    def delayed_set_heating(self, kwargs):
        """Wrapper to call __set_heating after a delay."""
        self.log(f"Executing delayed call to __set_heating kwargs={kwargs}")
        heat = kwargs.get("heat")
        self.log(f" __set_heating heat={heat}")
        if heat is not None and isinstance(heat, bool):
            self.log(f"Executing delayed call to __set_heating with heat={heat}")
            # Call the target function
            self.__set_heating(heat)

    def __set_heating(self, heat: bool):
        """Set the relay on/off"""
        is_heating = self.is_heating()
        if heat:
            if not is_heating:
                self.log("Turning heating on in set heating")
                self.turn_on(self.__switch_heating)
        else:
            self.log("Try heating off. if it is on")
            if is_heating:
                self.log("Turning heating off. in set heating")
                self.turn_off(self.__switch_heating)

    def getRoomByEntity(self,entity):
        for room in self.__rooms:
            climate=room[ATTR_THERMOSTATS]
            scheduler=room[ATTR_SCHEDULER]
            if  entity==climate or scheduler==entity:
                self.log(f"getRoomByEntity return {room}")
                return room
        self.log("getRoomByEntity return none")
        return None


    def scheduler_changed_temperature(self, entity, attribute, old, new, kwargs):
        """Event handler: target temperature", secure time lock to prevent multiple calls"""
        self.log(" called scheduler_changed_temperature ")
        self.log(f"entity: {entity} attribute: {attribute}, old: {old},new: {new}")
        self.print_state(entity)
        actualDT=datetime.now()
        five_seconds = timedelta(seconds=5)
        time_difference = actualDT - self.lastSwitchDt
        room=self.getRoomByEntity(entity)
        bbb = ATTR_SCHEDULE in entity
        self.log(f"room {room} ATTR_SCHEDULE in ent : {bbb}, time_difference {time_difference}")
        if ATTR_SCHEDULE in entity:
            self.log(f"MODE_SCHEDULE {MODE_SCHEDULE}")
            self.setMode(MODE_SCHEDULE,room[ATTR_ROOM_ID])
            self.__update_thermostat(room)
            return

    def target_changed(self, entity, attribute, old, new, kwargs):
        """Event handler: target temperature changed """
        self.log(" called target_changed")
        self.log(f"entity: {entity} attribute: {attribute}")
        self.log(f" old: {old},new: {new}")
        self.print_state(entity)
        room=self.getRoomByEntity(entity)
        self.log(f" old: {old},new: {new},room {room}")
        self.setMode(MODE_MANUAL,room[ATTR_ROOM_ID])

    def target_current_temp_changed(self, entity, attribute, old, new, kwargs):
        """Event handler: target_current_temp_changed", secure time lock to prevent multiple calls"""
        self.log(" called target_current_temp_changed")
        self.log(f"entity: {entity} attribute: {attribute}")
        self.log(f" old: {old},new: {new}")
        self.print_state(entity)
        room=self.getRoomByEntity(entity)
        self.log(f" old: {old},new: {new},room {room}")

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

    def get_attributes_shelly(self):
        attributes = self.get_state(self.__switch_heating, attribute="all")
        self.log(f" call get_attributes_shelly {attributes}")

    def print_state(self,entity):
        attributesT = self.get_state(entity, attribute="all")
        self.log(f" print_state attributesT :{attributesT}")

    def get_current_temperature(self,entity_thermostat) -> float:
        attributesT = self.get_state(entity_thermostat, attribute="all")
        currentTempValue = attributesT["attributes"].get('current_temperature')
        return float(currentTempValue)

    def get_follow_state(self,entity_thermostat) -> float:
        attributesT = self.get_state(entity_thermostat, attribute="all")
        #self.log(f" call get_follow_state attributesT :{attributesT}")
        follow = attributesT["attributes"].get('follow')
        #self.log(f" call get_follow_state {follow}")
        return bool(follow)

    def __set_thermostat(
            self, entity_id: str, target_temp: float, current_temp: float, boiler_mode: str,follow: bool
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
            f"mode {boiler_mode} ")
        #f"current temperature {current_temp}.")
        if current_temp is not None and target_temp is not None and boiler_mode is not None:
            attrs = {}
            #attrs[ATTR_CURRENT_TEMP] = current_temp
            attrs[ATTR_TEMPERATURE] = target_temp
            attrs[ATTR_HVAC_MODE] = boiler_mode
            attrs['preset_mode'] = 'None'
            attrs[ATTR_HVAC_MODES] = [HVAC_HEAT, HVAC_OFF]
            self.set_state(entity_id, state='None', attributes=attrs)
            self.call_service(
                "climate/set_temperature", entity_id=entity_id, temperature=target_temp
            )
            if follow:
                if current_temp-HYSTERESIS<target_temp:
                    self.log("slow call set heating")
                    delay_seconds = 1200
                    self.run_in(self.delayed_set_heating, delay_seconds,heat=False)
                else:
                    self.__set_heating(False)
            self.log(f" call set atribute ok {attrs}")

    def get_boilerMode(self) -> str:
        if self.is_heating():
            return HVAC_HEAT
        else:
            return HVAC_OFF

    def __update_thermostat(self, room: str = None):
        """Set the thermostats target temperature, current temperature and heating mode"""
        self.log(f" __update_thermostat start in room")
        room_mode=self.getMode(room)
        self.log(f"updating room with thermostat {room[ATTR_THERMOSTATS]}, room_mode {room_mode}")
        temperature = self.get_current_temperature(room[ATTR_THERMOSTATS])
        follow=self.get_follow_state(room[ATTR_SCHEDULER])
        demandTemp = self.get_demand_temperature_by_mode(room_mode,room)
        self.log(f"temperature {temperature},follow {follow}, target_temperature {demandTemp}")
        boiler_mode = self.get_boilerMode()
        self.__set_thermostat(room[ATTR_THERMOSTATS], demandTemp, temperature, boiler_mode,follow)




