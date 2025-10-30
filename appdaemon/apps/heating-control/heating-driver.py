import math
from typing import Optional
import appdaemon.plugins.hass.hassapi as hass


ATTR_SWITCH_HEATING = "switch_heating"
ATTR_ROOMS = "rooms"
HYSTERESIS = 1 # in celsius
ATTR_DEFAULT_MODE = "mode"


# 2 type of state
STATE_NORMAL = "normal"

ATTR_SCHEDULER = "scheduler"
ATTR_THERMOSTATS = "thermostat"
ATTR_ROOM_ID = "room_id"

ATTR_CURRENT_TEMP = "current_temperature"
ATTR_TEMPERATURE = "temperature"
ATTR_ENTITY_ID = "entity_id"

#
# Heating App
#
# Args:
#

class Heating(hass.Hass):

    def initialize(self):
        self.log("Hello from AppDaemon")
        self.log("You are now ready to Heating!")
        self.__rooms = self.args.get(ATTR_ROOMS)
        self.log(f"rooms {self.__rooms}")
        self.initialize_switch_heating()
        self.init_all_rooms()

    def initialize_switch_heating(self):
        """
        Initializes the heating switch entity from arguments and checks for errors.
        """
        self.__switch_heating=None
        try:
            self.__switch_heating = self.args.get(ATTR_SWITCH_HEATING)
            state = self.get_state(self.__switch_heating)
            self.log(f"initialize_switch_heating attributes {state}", level="INFO")
            if state=="unavailable" or state is None:
                self.__switch_heating=None
            self.log(f"initialize_switch_heating 2 {self.__switch_heating}", level="INFO")
        except Exception as e:
            self.log(f"initialize_switch_heating error : {self.__switch_heating}", level="WARN")
            self.__switch_heating=None

    def init_all_rooms(self):
        for room in self.__rooms:
            entity_climate=room[ATTR_THERMOSTATS]
            self.log(f" call init_all_rooms: {entity_climate}")
            self.get_attributes(room)
            self.handle = self.listen_state(self.target_current_temp_changed,entity_climate,attribute=ATTR_CURRENT_TEMP)
            entity_scheduler=room[ATTR_SCHEDULER]
            foll=self.get_follow_state(entity_scheduler)
            self.log(f" call init_all_rooms: {entity_scheduler},foll:{foll}")
            self.handle = self.listen_state(self.scheduler_changed_temperature,entity_scheduler,attribute="temperature")
            roomId=room[ATTR_ROOM_ID]

    def delayed_set_heating(self, kwargs):
        """Wrapper to call __set_heating after a delay."""
        heat = kwargs.get("heat")
        self.log(f" __set_heating heat={heat}")
        if heat is not None and isinstance(heat, bool):
            self.log(f"Executing delayed call to __set_heating with heat={heat}")
            # Call the target function
            self.__set_heating(heat)

    def __set_heating(self, heat: bool):
        """Set the relay on/off"""
        is_heating = self.is_heating()
        self.log(f"call __set_heating  {heat}, {is_heating}  ")
        if is_heating is None:
            self.log("WARNING: Current heating state is UNKNOWN (None). Proceeding with requested action.", level="WARNING")
            return
        if heat:
            if not is_heating:
                self.log("Turning heating on in set heating")
                self.turn_on(self.__switch_heating)
        else:
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

    def target_current_temp_changed(self, entity, attribute, old, new, kwargs):
        """Event handler: target_current_temp_changed", secure time lock to prevent multiple calls"""
        self.log(f" called target_current_temp_changed entity: {entity} attribute: {attribute}")
        room=self.getRoomByEntity(entity)
        self.log(f" old: {old},new: {new},room {room}")
        demandTemp=self.get_demand_temperature(room[ATTR_SCHEDULER])
        follow=self.get_follow_state(entity)
        self.log(f" follow: {follow},demandTemp: {demandTemp}")
        newI=int(new)
        if follow and newI-HYSTERESIS<demandTemp:
            delay_seconds = 1200
            self.__set_heating(True)
            self.run_in(self.delayed_set_heating, delay_seconds,heat=False)

    def scheduler_changed_temperature(self, entity, attribute, old, new, kwargs):
        """Event handler: target temperature", this changed is linked to demand temperature
        and subsequently call target_demand_temp_changed"""
        self.log(f"called scheduler_changed_temperature  entity: {entity} attribute: {attribute}, old: {old},new: {new}")
        room=self.getRoomByEntity(entity)
        self.log(f" old: {old},new: {new},room {room}")
        newI=int(new)
        demandTemp=self.get_demand_temperature(room[ATTR_SCHEDULER])
        follow=self.get_follow_state(entity)
        self.log(f" follow: {follow},demandTemp: {demandTemp}")
        if follow and newI-HYSTERESIS<demandTemp:
            delay_seconds = 1200
            self.__set_heating(True)
            self.run_in(self.delayed_set_heating, delay_seconds,heat=False)

    def is_heating(self) -> Optional[bool]:
        """
        Checks heating state. Returns True/False, or None if the state is unresolvable.
        """
        self.log(f"is_heating: State for {self.__switch_heating} ")
        if not self.__switch_heating:
            self.log("Heating switch entity ID is not set.")
            return None  # Cannot proceed

        try:
            state = self.get_state(self.__switch_heating)
            self.log(f"Heating switch entity {state}.")
            if state is None:
                self.log(f"Warning: State for {self.__switch_heating} is None (entity unavailable).", level="WARNING")
                return None # The state is unknown/unavailable

            # If the state is found, return the boolean result
            return bool(str(state).lower() == "on")

        except Exception as e:
            self.error(f"Unexpected error while checking heating state: {e}")
            return None

    def get_demand_temperature(self,entity) -> float:
        """Return demand temperature  from entity climate, or schedule(alsou return math.nan)"""
        attributes = self.get_state(entity, attribute="all")
        temperature = attributes["attributes"].get("temperature")
        if temperature == 'None':
            return math.nan
        return float(temperature)

    def get_attributes(self,room):
        entity=room[ATTR_SCHEDULER]
        attributes = self.get_state(entity, attribute="all")
        self.log(f" call get_attributes {attributes}")

    def get_attributes_shelly(self):
        attributes = self.get_state(self.__switch_heating, attribute="all")
        self.log(f" call get_attributes_shelly {attributes}")

    def print_state(self,entity):
        attributesT = self.get_state(entity, attribute="all")

    def get_follow_state(self,entity_scheduler) -> bool:
        self.log(f" call get_follow_state entity_thermostat:{entity_scheduler}")
        attributesT = self.get_state(entity_scheduler, attribute="all")
        follow = attributesT["attributes"].get('follow')
        return bool(follow)
