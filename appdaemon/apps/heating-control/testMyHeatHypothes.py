ATTR_ROOMS = "rooms"

# mock attribute data (just like in apps.yaml)
test_attributes = {
    ATTR_ROOMS: [
        {
            "sensor": "sensor.teplota_living_toom",
            "day_night": "input_boolean.livingroom_day_night",
            "temperature_day": "input_number.livingroom_day",
            "temperature_night": "input_number.livingroom_night",
            "thermostats": [
                "climate.termostat_living_room",
                "climate.termostat_dining_area"
            ]
        },
        {
            "sensor": "sensor.teplota_bedroom",
            "day_night": "input_boolean.bedroom_day_night",
            "temperature_day": "input_number.bedroom_day",
            "temperature_night": "input_number.bedroom_night",
            "thermostats": [
                "climate.termostat_bedroom"
            ]
        }
    ]
}

# iterate for testing
for room in test_attributes[ATTR_ROOMS]:
    print(f"Room sensor: {room['sensor']}")
    print(f" Day/Night toggle: {room['day_night']}")
    print(f" Temperatures: {room['temperature_day']} / {room['temperature_night']}")
    print(f" Thermostats: {', '.join(room['thermostats'])}")
    print("----")