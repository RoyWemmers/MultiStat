"""
Home Assistant integration for reading sensors and controlling entities.
"""
import os
import json
import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HomeAssistantAPI:
    """Home Assistant API client."""
    
    def __init__(self):
        """Initialize Home Assistant API client."""
        self.base_url = os.environ.get('SUPERVISOR_URL', 'http://supervisor')
        self.token = os.environ.get('SUPERVISOR_TOKEN', '')
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the API session."""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            headers=headers
        )
        logger.info("Home Assistant API client started")
    
    async def stop(self):
        """Stop the API session."""
        if self.session:
            await self.session.close()
            logger.info("Home Assistant API client stopped")
    
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get state of a Home Assistant entity."""
        if not self.session:
            await self.start()
        
        try:
            url = f'/core/api/states/{entity_id}'
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"Failed to get state for {entity_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting state for {entity_id}: {e}")
            return None
    
    async def get_temperature(self, entity_id: str) -> Optional[float]:
        """Get temperature value from a sensor entity."""
        state = await self.get_state(entity_id)
        if state and 'state' in state:
            try:
                return float(state['state'])
            except (ValueError, TypeError):
                logger.warning(f"Could not parse temperature from {entity_id}: {state['state']}")
        return None
    
    async def set_valve_position(self, entity_id: str, position: float):
        """Set valve position (0-100) for a cover or number entity."""
        if not self.session:
            await self.start()
        
        try:
            # Try as number entity first
            url = f'/core/api/services/number/set_value'
            data = {
                'entity_id': entity_id,
                'value': position
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} to {position}%")
                    return True
            
            # Try as cover entity (position)
            url = f'/core/api/services/cover/set_cover_position'
            data = {
                'entity_id': entity_id,
                'position': int(position)
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} to {position}%")
                    return True
            
            logger.warning(f"Failed to set valve position for {entity_id}")
            return False
        except Exception as e:
            logger.error(f"Error setting valve position for {entity_id}: {e}")
            return False
    
    async def update_room_temperatures(self, room_manager):
        """Update all room temperatures from Home Assistant sensors."""
        tasks = []
        for room in room_manager.rooms:
            task = self._update_single_room(room_manager, room)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _update_single_room(self, room_manager, room):
        """Update temperature for a single room."""
        temp = await self.get_temperature(room.current_temp_sensor)
        if temp is not None:
            room_manager.update_room_temperature(room.name, temp)
    
    async def set_thermostat_temperature(self, entity_id: str, temperature: float):
        """Set target temperature on a thermostat entity."""
        if not self.session:
            await self.start()
        
        try:
            # Try climate.set_temperature service
            url = f'/core/api/services/climate/set_temperature'
            data = {
                'entity_id': entity_id,
                'temperature': temperature
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} temperature to {temperature}°C")
                    return True
            
            # Try number.set_value if it's a number entity
            url = f'/core/api/services/number/set_value'
            data = {
                'entity_id': entity_id,
                'value': temperature
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} value to {temperature}")
                    return True
            
            logger.warning(f"Failed to set thermostat temperature for {entity_id}")
            return False
        except Exception as e:
            logger.error(f"Error setting thermostat temperature for {entity_id}: {e}")
            return False
    
    async def get_hrv_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get state of an HRV entity."""
        return await self.get_state(entity_id)
    
    async def set_hrv_mode(self, entity_id: str, mode: str):
        """Set mode for an HRV entity (e.g., 'on', 'off', 'auto')."""
        if not self.session:
            await self.start()
        
        try:
            # Try fan.set_preset_mode if it's a fan entity
            url = f'/core/api/services/fan/set_preset_mode'
            data = {
                'entity_id': entity_id,
                'preset_mode': mode
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} preset mode to {mode}")
                    return True
            
            # Try climate.set_hvac_mode if it's a climate entity
            url = f'/core/api/services/climate/set_hvac_mode'
            data = {
                'entity_id': entity_id,
                'hvac_mode': mode
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} HVAC mode to {mode}")
                    return True
            
            # Try input_select.select_option if it's an input_select
            url = f'/core/api/services/input_select/select_option'
            data = {
                'entity_id': entity_id,
                'option': mode
            }
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Set {entity_id} option to {mode}")
                    return True
            
            logger.warning(f"Failed to set HRV mode for {entity_id}")
            return False
        except Exception as e:
            logger.error(f"Error setting HRV mode for {entity_id}: {e}")
            return False
    
    async def update_valve_positions(self, room_manager):
        """Update all HRV valve positions in Home Assistant."""
        tasks = []
        for room in room_manager.rooms:
            for valve in room.hrv_valves:
                task = self.set_valve_position(valve.valve_entity, valve.current_position)
                tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def update_hrv_devices(self, room_manager):
        """Update HRV device states based on room requirements."""
        tasks = []
        for room in room_manager.rooms:
            if room.hrv_entity:
                # Enable HRV if room needs heating
                if room.needs_heating():
                    task = self.set_hrv_mode(room.hrv_entity, 'on')
                else:
                    # Could set to 'auto' or 'off' based on preference
                    task = self.set_hrv_mode(room.hrv_entity, 'auto')
                tasks.append(task)
        
        await asyncio.gather(*tasks)