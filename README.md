# Multi-Room Thermostat Add-on for Home Assistant

A Home Assistant add-on that provides multi-room thermostat functionality with HRV (Heat Recovery Ventilator) valve control and OpenTherm boiler integration.

## Features

- **Multi-Room Support**: Manage multiple rooms with individual target temperatures
- **OpenTherm Integration**: Communicate with central boiler using OpenTherm protocol
- **Intelligent Boiler Control**: Automatically controls boiler based on the room with the highest temperature difference
- **HRV Valve Control**: PID-based control for HRV valve positions in each room
- **Home Assistant Integration**: Seamlessly integrates with Home Assistant sensors and entities

## How It Works

1. **Temperature Monitoring**: Continuously reads current temperatures from Home Assistant sensors for each configured room
2. **Room Selection**: Identifies the room with the highest temperature difference (target - current)
3. **Boiler/Thermostat Control**: 
   - Sends target and current temperature of the selected room to the boiler via OpenTherm (if configured)
   - Controls the central thermostat entity (if configured) with the target temperature
4. **HRV Device Control**: Automatically enables/disables HRV devices based on room heating requirements
5. **HRV Valve Control**: Uses PID controllers to adjust HRV valve positions based on temperature differences in each room

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

opentherm:
  serial_port: "/dev/ttyUSB0"
  baudrate: 9600

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
- **central_thermostat_entity**: (Optional) Home Assistant entity ID of the central thermostat (climate or number entity). If configured, the add-on will control this thermostat in addition to or instead of OpenTherm.

#### OpenTherm
- **serial_port**: Serial port device path (e.g., `/dev/ttyUSB0`)
- **baudrate**: Serial communication baudrate (typically 9600)

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
- OpenTherm-compatible boiler with serial interface
- HRV valves controllable via Home Assistant (number or cover entities)
- Temperature sensors in each room

## Hardware Setup

1. Connect OpenTherm interface to your boiler (typically via serial/USB adapter)
2. Ensure HRV valves are integrated into Home Assistant
3. Install temperature sensors in each room and add them to Home Assistant

## Troubleshooting

### OpenTherm Connection Issues
- Verify the serial port path is correct (`/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
- Check serial port permissions
- Ensure baudrate matches your OpenTherm interface

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