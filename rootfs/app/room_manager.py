"""
Multi-room thermostat manager.
"""
import logging
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HRVValve:
    """HRV valve configuration and state."""
    name: str
    valve_entity: str
    kp: float
    ki: float
    kd: float
    current_position: float = 0.0
    pid_controller: Optional[object] = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialize PID controller after object creation."""
        # Import here to avoid circular imports
        # Using absolute import since main.py adds app directory to path
        from pid_controller import PIDController
        self.pid_controller = PIDController(
            kp=self.kp,
            ki=self.ki,
            kd=self.kd,
            setpoint=0.0,
            output_limits=(0.0, 100.0)
        )


@dataclass
class Room:
    """Room configuration and state."""
    name: str
    target_temp: float
    current_temp_sensor: str
    hrv_entity: str
    hrv_valves: List[HRVValve]
    current_temp: Optional[float] = None
    
    def get_temperature_difference(self) -> float:
        """Calculate temperature difference from target."""
        if self.current_temp is None:
            return 0.0
        return abs(self.target_temp - self.current_temp)
    
    def needs_heating(self) -> bool:
        """Check if room needs heating."""
        if self.current_temp is None:
            return False
        return self.current_temp < self.target_temp


class RoomManager:
    """Manages multiple rooms and their HRV valves."""
    
    def __init__(self, rooms_config: List[Dict]):
        """Initialize room manager with configuration."""
        self.rooms: List[Room] = []
        self._load_rooms(rooms_config)
        
    def _load_rooms(self, rooms_config: List[Dict]):
        """Load rooms from configuration."""
        self.rooms = []
        for room_config in rooms_config:
            hrv_valves = []
            for valve_config in room_config.get('hrv_valves', []):
                valve = HRVValve(
                    name=valve_config['name'],
                    valve_entity=valve_config['valve_entity'],
                    kp=valve_config.get('kp', 1.0),
                    ki=valve_config.get('ki', 0.1),
                    kd=valve_config.get('kd', 0.05)
                )
                hrv_valves.append(valve)
            
            room = Room(
                name=room_config['name'],
                target_temp=room_config['target_temp'],
                current_temp_sensor=room_config['current_temp_sensor'],
                hrv_entity=room_config.get('hrv_entity', ''),
                hrv_valves=hrv_valves
            )
            self.rooms.append(room)
            logger.info(f"Loaded room: {room.name} with {len(hrv_valves)} HRV valves")
    
    def get_room_with_highest_difference(self) -> Optional[Room]:
        """Get the room with the highest temperature difference."""
        if not self.rooms:
            return None
        
        # Filter rooms that need heating and have current temperature
        rooms_needing_heat = [
            room for room in self.rooms 
            if room.needs_heating() and room.current_temp is not None
        ]
        
        if not rooms_needing_heat:
            return None
        
        # Return room with highest temperature difference
        return max(rooms_needing_heat, key=lambda r: r.get_temperature_difference())
    
    def update_room_temperature(self, room_name: str, temperature: float):
        """Update current temperature for a room."""
        for room in self.rooms:
            if room.name == room_name:
                room.current_temp = temperature
                logger.debug(f"Updated {room_name} temperature to {temperature}°C")
                return
        logger.warning(f"Room {room_name} not found")
    
    def calculate_hrv_positions(self, room: Room):
        """Calculate HRV valve positions for a room using PID control."""
        if room.current_temp is None:
            return
        
        # Calculate error (difference from target)
        error = room.target_temp - room.current_temp
        
        for valve in room.hrv_valves:
            # Set PID setpoint to 0 (we want to minimize error)
            valve.pid_controller.set_setpoint(0.0)
            
            # Update PID with current error
            # Positive error means room is too cold, so open valve more
            valve_position = valve.pid_controller.update(-error)
            
            # Ensure valve position is between 0 and 100
            valve_position = max(0.0, min(100.0, valve_position))
            valve.current_position = valve_position
            
            logger.debug(
                f"Room {room.name}, Valve {valve.name}: "
                f"Error={error:.2f}°C, Position={valve_position:.1f}%"
            )
    
    def get_control_temperatures(self) -> Optional[tuple]:
        """
        Get target and current temperatures for boiler control.
        Returns tuple of (target_temp, current_temp) for room with highest difference.
        """
        room = self.get_room_with_highest_difference()
        if room and room.current_temp is not None:
            return (room.target_temp, room.current_temp)
        return None