import appdaemon.plugins.hass.hassapi as hass


ATTR_SWITCH_HEATING = "switch_heating"
ATTR_ROOMS = "rooms"
HYSTEREZE= 1 # in celsius
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
        self.run_every(self.run_periodic_rooms, "now", 2 * 60)

    def run_periodic(self, kwargs):
        """This method will be called every 5 minutes"""
        self.log("Running periodic update...", level="INFO")
        entity_id = "schedule.obyvak_plan"
        state = self.get_state(entity_id)
        attributes = self.get_state(entity_id, attribute="all")
        entities = ["schedule.obyvak_plan", "climate.obyvak_termostat_1"]
        for enti in entities:
            self.printparams(enti)

    def run_periodic_rooms(self, kwargs):
        """This method will be called every 5 minutes"""
        self.log("Running periodic update...", level="INFO")
        heatOnB = False
        for room in self.__rooms:
            self.log(f"mistnost plan:  {room['scheduler']} ")
            entSched=room['scheduler']
            attributes = self.get_state(entSched, attribute="all")
            temperature = attributes["attributes"].get("temperature")
            demandTemp=float(temperature)
            self.log(f" demandTemp value: {demandTemp}")
            entThermos=room['thermostats']
            attributesT = self.get_state(entThermos, attribute="all")
            currentTemp='current_temperature'
            currentTempValue = attributesT["attributes"].get(currentTemp)
            currTemp=float(currentTempValue)
            self.log(f"currentTempValue: {currTemp}")
            if demandTemp>currTemp+HYSTEREZE:
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

    def is_heating(self) -> bool:
        return bool(self.get_state(self.__switch_heating).lower() == "on")

    def printparams(self,entity_id):
        state = self.get_state(entity_id)
        attributes = self.get_state(entity_id, attribute="all")
        self.log(f"Entity {entity_id} state: {state}")
        self.log(f"Entity {entity_id} full content: {attributes}")
        temperature = attributes["attributes"].get("temperature")
        self.log(f" temperature value: {temperature}")

    def checkTemperature(self, demandTemperature,actualTemperature):
        self.log(f" temperature value: {temperature}")

