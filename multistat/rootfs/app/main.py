#!/usr/bin/env python3
"""
Multi-Room Thermostat - Main Application
"""
import os
import sys
import json
import logging
import asyncio
import signal
from pathlib import Path

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

from room_manager import RoomManager
from ha_integration import HomeAssistantAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiRoomThermostat:
    """Main application class for multi-room thermostat."""
    
    def __init__(self, config_path: str = '/data/options.json'):
        """Initialize the thermostat application."""
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        
        # Initialize components
        self.room_manager = RoomManager(self.config.get('rooms', []))
        self.ha_api = HomeAssistantAPI()
        
        # Central thermostat entity (optional)
        self.central_thermostat_entity = self.config.get('central_thermostat_entity', '')
        
        # Boiler temperature sensor entities
        self.boiler_target_sensor = self.config.get('boiler_target_sensor', 'sensor.multistat_boiler_target_temp')
        self.boiler_current_sensor = self.config.get('boiler_current_sensor', 'sensor.multistat_boiler_current_temp')
        
        self.update_interval = self.config.get('update_interval', 5)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration: {e}")
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _update_temperatures(self):
        """Update room temperatures from Home Assistant."""
        await self.ha_api.update_room_temperatures(self.room_manager)
    
    async def _update_boiler_temperatures(self):
        """Output boiler control temperatures based on room with highest difference."""
        temps = self.room_manager.get_control_temperatures()
        if temps:
            target_temp, current_temp = temps
            room = self.room_manager.get_room_with_highest_difference()
            logger.info(
                f"Boiler control for room '{room.name}': "
                f"Target={target_temp}°C, Current={current_temp}°C"
            )
            
            # Publish temperatures as Home Assistant sensors
            await self.ha_api.set_sensor_state(
                self.boiler_target_sensor,
                target_temp,
                unit_of_measurement='°C',
                friendly_name='Boiler Target Temperature',
                device_class='temperature'
            )
            await self.ha_api.set_sensor_state(
                self.boiler_current_sensor,
                current_temp,
                unit_of_measurement='°C',
                friendly_name='Boiler Current Temperature',
                device_class='temperature'
            )
            
            # Control via central thermostat entity if configured
            if self.central_thermostat_entity:
                await self.ha_api.set_thermostat_temperature(
                    self.central_thermostat_entity,
                    target_temp
                )
        else:
            logger.debug("No room needs heating, setting boiler temperatures to None")
            # Set sensors to None when no room needs heating
            await self.ha_api.set_sensor_state(
                self.boiler_target_sensor,
                None,
                unit_of_measurement='°C',
                friendly_name='Boiler Target Temperature',
                device_class='temperature'
            )
            await self.ha_api.set_sensor_state(
                self.boiler_current_sensor,
                None,
                unit_of_measurement='°C',
                friendly_name='Boiler Current Temperature',
                device_class='temperature'
            )
    
    async def _update_hrv_valves(self):
        """Update HRV valve positions using PID control."""
        for room in self.room_manager.rooms:
            if room.current_temp is not None:
                # Calculate valve positions for this room
                self.room_manager.calculate_hrv_positions(room)
        
        # Update valve positions in Home Assistant
        await self.ha_api.update_valve_positions(self.room_manager)
    
    async def _update_hrv_devices(self):
        """Update HRV device states based on room requirements."""
        await self.ha_api.update_hrv_devices(self.room_manager)
    
    async def _main_loop(self):
        """Main control loop."""
        logger.info("Starting main control loop")
        
        while self.running:
            try:
                # Update room temperatures from Home Assistant
                await self._update_temperatures()
                
                # Output boiler temperatures (room with highest difference)
                await self._update_boiler_temperatures()
                
                # Update HRV valve positions using PID
                await self._update_hrv_valves()
                
                # Update HRV device states based on room requirements
                await self._update_hrv_devices()
                
                # Wait for next update cycle
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(self.update_interval)
    
    async def start(self):
        """Start the thermostat application."""
        logger.info("Starting Multi-Room Thermostat")
        
        try:
            # Start Home Assistant API
            await self.ha_api.start()
            
            # Initialize boiler temperature sensors
            await self.ha_api.create_sensor(
                self.boiler_target_sensor,
                friendly_name='Boiler Target Temperature',
                device_class='temperature',
                unit_of_measurement='°C'
            )
            await self.ha_api.create_sensor(
                self.boiler_current_sensor,
                friendly_name='Boiler Current Temperature',
                device_class='temperature',
                unit_of_measurement='°C'
            )
            
            if self.central_thermostat_entity:
                logger.info(f"Using central thermostat: {self.central_thermostat_entity}")
            
            logger.info(f"Boiler temperatures will be published to:")
            logger.info(f"  Target: {self.boiler_target_sensor}")
            logger.info(f"  Current: {self.boiler_current_sensor}")
            
            # Start main loop
            self.running = True
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the application."""
        logger.info("Shutting down Multi-Room Thermostat")
        
        self.running = False
        
        # Stop Home Assistant API
        await self.ha_api.stop()
        
        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    # Determine config path
    config_path = '/data/options.json'
    if not os.path.exists(config_path):
        # Fallback for development
        config_path = os.path.join(os.path.dirname(__file__), 'options.json')
        if not os.path.exists(config_path):
            logger.error("Configuration file not found")
            sys.exit(1)
    
    # Create and run application
    app = MultiRoomThermostat(config_path)
    
    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()