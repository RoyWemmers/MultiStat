# Multi-Room Thermostat Add-on for Home Assistant

A Home Assistant add-on that provides multi-room thermostat functionality with HRV (Heat Recovery Ventilator) valve control and boiler temperature output.

## Features

- **Multi-Room Support**: Manage multiple rooms with individual target temperatures
- **Boiler Temperature Output**: Publishes target and current temperatures from the room with highest difference as Home Assistant sensors
- **Intelligent Room Selection**: Automatically selects the room with the highest temperature difference for boiler control
- **HRV Valve Control**: PID-based control for HRV valve positions in each room
- **HRV Device Control**: Automatically enables/disables HRV devices based on room heating requirements
- **Home Assistant Integration**: Seamlessly integrates with Home Assistant sensors and entities

## How It Works

1. **Temperature Monitoring**: Continuously reads current temperatures from Home Assistant sensors for each configured room
2. **Room Selection**: Identifies the room with the highest temperature difference (target - current)
3. **Boiler Temperature Output**: 
   - Publishes target and current temperature of the selected room as Home Assistant sensors
   - These sensors can be read by another device (e.g., OpenTherm controller) to control the boiler
   - Sensors are set to `unknown` when no room needs heating
4. **Central Thermostat Control**: Optionally controls a central thermostat entity (if configured) with the target temperature
5. **HRV Device Control**: Automatically enables/disables HRV devices based on room heating requirements
6. **HRV Valve Control**: Uses PID controllers to adjust HRV valve positions based on temperature differences in each room

## Installation

1. Copy this add-on to your Home Assistant add-ons directory (typically `/config/addons/` or `/addons/`)
2. Add the repository to Home Assistant if needed
3. Install the "Multi-Room Thermostat" add-on from the Supervisor panel
4. Configure the add-on (see Configuration section)
5. Start the add-on

## Configuration

The add-on is configured through the Home Assistant add-on configuration panel. Here's an example configuration:

```yaml
rooms:
  - name: "Living Room"
    target_temp: 21.0
    current_temp_sensor: "sensor.living_room_temperature"
    hrv_entity: "fan.living_room_hrv"
    hrv_valves:
      - name: "Living Room HRV Valve 1"
        valve_entity: "number.living_room_hrv_valve_1"
        kp: 1.0
        ki: 0.1
        kd: 0.05
      - name: "Living Room HRV Valve 2"
        valve_entity: "number.living_room_hrv_valve_2"
        kp: 1.0
        ki: 0.1
        kd: 0.05
  - name: "Bedroom"
    target_temp: 20.0
    current_temp_sensor: "sensor.bedroom_temperature"
    hrv_entity: "fan.bedroom_hrv"
    hrv_valves:
      - name: "Bedroom HRV Valve"
        valve_entity: "number.bedroom_hrv_valve"
        kp: 1.2
        ki: 0.15
        kd: 0.08

central_thermostat_entity: "climate.main_thermostat"

boiler_target_sensor: "sensor.multistat_boiler_target_temp"
boiler_current_sensor: "sensor.multistat_boiler_current_temp"

update_interval: 5
```

### Configuration Options

#### Rooms
- **name**: Name of the room (for logging purposes)
- **target_temp**: Target temperature in Celsius
- **current_temp_sensor**: Home Assistant entity ID of the temperature sensor
- **hrv_entity**: Home Assistant entity ID of the main HRV device for this room (fan, climate, or input_select entity)
- **hrv_valves**: List of HRV valves for this room
  - **name**: Name of the valve
  - **valve_entity**: Home Assistant entity ID (number or cover entity)
  - **kp**: Proportional gain for PID controller
  - **ki**: Integral gain for PID controller
  - **kd**: Derivative gain for PID controller

#### Central Thermostat
- **central_thermostat_entity**: (Optional) Home Assistant entity ID of the central thermostat (climate or number entity). If configured, the add-on will control this thermostat with the target temperature.

#### Boiler Temperature Sensors
- **boiler_target_sensor**: Home Assistant sensor entity ID where the target temperature will be published (default: `sensor.multistat_boiler_target_temp`)
- **boiler_current_sensor**: Home Assistant sensor entity ID where the current temperature will be published (default: `sensor.multistat_boiler_current_temp`)

These sensors output the target and current temperatures from the room with the highest temperature difference. Another device (e.g., an OpenTherm controller) can read these sensors to control the boiler.

#### Update Interval
- **update_interval**: Update interval in seconds (default: 5)

## PID Controller Tuning

The PID controller adjusts HRV valve positions based on the temperature difference. Here are some tuning guidelines:

- **Kp (Proportional)**: Higher values = faster response, but may cause overshoot
- **Ki (Integral)**: Eliminates steady-state error, but can cause oscillation if too high
- **Kd (Derivative)**: Reduces overshoot and improves stability

Start with default values (Kp=1.0, Ki=0.1, Kd=0.05) and adjust based on your system's response.

## Requirements

- Home Assistant with Supervisor
- HRV valves controllable via Home Assistant (number or cover entities)
- Temperature sensors in each room
- Another device/system to read the boiler temperature sensors and control the boiler (e.g., OpenTherm controller)

## Hardware Setup

1. Ensure HRV valves are integrated into Home Assistant
2. Install temperature sensors in each room and add them to Home Assistant
3. Configure another device/system to read the boiler temperature sensors (`boiler_target_sensor` and `boiler_current_sensor`) and control your boiler accordingly

## Boiler Integration

The add-on publishes two sensor values that represent the boiler control temperatures:
- **Target Temperature**: The desired temperature for the room with highest difference
- **Current Temperature**: The current temperature of that room

These sensors can be read by:
- Another Home Assistant automation/script
- An external OpenTherm controller device
- Any system that can read Home Assistant sensor values

Example Home Assistant automation to read these values:
```yaml
automation:
  - alias: "Read Boiler Temperatures"
    trigger:
      - platform: state
        entity_id: sensor.multistat_boiler_target_temp
    action:
      - service: system_log.write
        data:
          message: "Target: {{ states('sensor.multistat_boiler_target_temp') }}, Current: {{ states('sensor.multistat_boiler_current_temp') }}"
```

## Troubleshooting

### Boiler Temperature Sensors Not Updating
- Verify the sensor entity IDs are correct in the configuration
- Check that sensors are being created in Home Assistant (check Developer Tools > States)
- Review add-on logs for errors

### Valve Control Not Working
- Verify valve entity IDs are correct
- Check that entities are of type `number` or `cover`
- Ensure entities are accessible from the add-on

### Temperature Not Updating
- Verify sensor entity IDs are correct
- Check that sensors are reporting values in Home Assistant
- Review add-on logs for errors

## Development

To build and test locally:

```bash
# Build the add-on
docker build -t multistat .

# Run tests (if available)
python3 -m pytest tests/
```

## License

MIT License

## Support

For issues and feature requests, please open an issue on the project repository.