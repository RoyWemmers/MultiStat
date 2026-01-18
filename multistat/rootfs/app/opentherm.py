"""
OpenTherm communication module for boiler control.
"""
import serial
import struct
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class OpenThermProtocol:
    """OpenTherm protocol implementation."""
    
    # Message types
    READ_DATA = 0
    WRITE_DATA = 1
    INVALID_DATA = 2
    RESERVED = 3
    
    # Data IDs
    STATUS = 0
    TSET = 1  # Control setpoint (target temperature)
    TBOILER = 25  # Boiler water temperature
    
    def __init__(self, serial_port: str, baudrate: int = 9600):
        """Initialize OpenTherm connection."""
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        
    def connect(self):
        """Connect to OpenTherm interface."""
        try:
            self.serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            logger.info(f"Connected to OpenTherm on {self.serial_port}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenTherm: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from OpenTherm interface."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Disconnected from OpenTherm")
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate checksum for OpenTherm message."""
        return sum(data) & 0xFF
    
    def _create_message(self, msg_type: int, data_id: int, data_value: int) -> bytes:
        """Create an OpenTherm message."""
        # OpenTherm message format: [Start byte, MSB, LSB, Checksum]
        msb = (msg_type << 6) | ((data_id >> 8) & 0x3F)
        lsb = data_id & 0xFF
        data_bytes = struct.pack('>H', data_value)
        msb_data = (msb << 8) | data_bytes[0]
        lsb_data = (lsb << 8) | data_bytes[1]
        
        msg = bytes([0x00, msb_data, lsb_data, 0x00])
        checksum = self._calculate_checksum(msg[1:3])
        msg = bytes([0x00, msb_data, lsb_data, checksum])
        return msg
    
    def _parse_message(self, msg: bytes) -> Optional[Tuple[int, int, int]]:
        """Parse an OpenTherm message."""
        if len(msg) != 4:
            return None
        
        checksum = self._calculate_checksum(msg[1:3])
        if checksum != msg[3]:
            logger.warning("Invalid checksum in OpenTherm message")
            return None
        
        msb = msg[1]
        lsb = msg[2]
        
        msg_type = (msb >> 6) & 0x03
        data_id = ((msb & 0x3F) << 8) | lsb
        data_value = ((msb & 0x0F) << 12) | ((lsb & 0xFF) << 4)
        
        return (msg_type, data_id, data_value)
    
    def set_target_temperature(self, temperature: float):
        """Set target temperature for boiler (TSET)."""
        if not self.serial or not self.serial.is_open:
            raise ConnectionError("OpenTherm not connected")
        
        # Convert temperature to OpenTherm format (signed fixed point, 0.1°C resolution)
        temp_value = int(temperature * 10) & 0xFFFF
        
        msg = self._create_message(self.WRITE_DATA, self.TSET, temp_value)
        self.serial.write(msg)
        time.sleep(0.1)
        
        # Read response
        response = self.serial.read(4)
        if response:
            parsed = self._parse_message(response)
            if parsed:
                logger.info(f"Set target temperature to {temperature}°C")
                return True
        
        logger.warning("Failed to set target temperature")
        return False
    
    def get_boiler_temperature(self) -> Optional[float]:
        """Get current boiler water temperature."""
        if not self.serial or not self.serial.is_open:
            raise ConnectionError("OpenTherm not connected")
        
        msg = self._create_message(self.READ_DATA, self.TBOILER, 0)
        self.serial.write(msg)
        time.sleep(0.1)
        
        response = self.serial.read(4)
        if response:
            parsed = self._parse_message(response)
            if parsed:
                msg_type, data_id, data_value = parsed
                if data_id == self.TBOILER:
                    # Convert from OpenTherm format (signed fixed point, 0.1°C resolution)
                    temp = (data_value >> 4) / 10.0
                    return temp
        
        return None
    
    def get_status(self) -> Optional[dict]:
        """Get boiler status."""
        if not self.serial or not self.serial.is_open:
            raise ConnectionError("OpenTherm not connected")
        
        msg = self._create_message(self.READ_DATA, self.STATUS, 0)
        self.serial.write(msg)
        time.sleep(0.1)
        
        response = self.serial.read(4)
        if response:
            parsed = self._parse_message(response)
            if parsed:
                msg_type, data_id, data_value = parsed
                if data_id == self.STATUS:
                    return {
                        'ch_enabled': bool(data_value & 0x01),
                        'dhw_enabled': bool(data_value & 0x02),
                        'cooling_enabled': bool(data_value & 0x04),
                        'otc_active': bool(data_value & 0x08),
                        'ch2_enabled': bool(data_value & 0x10),
                        'fault': bool(data_value & 0x80)
                    }
        
        return None


class OpenThermController:
    """High-level OpenTherm controller."""
    
    def __init__(self, serial_port: str, baudrate: int = 9600):
        """Initialize OpenTherm controller."""
        self.protocol = OpenThermProtocol(serial_port, baudrate)
        self.connected = False
        
    def start(self):
        """Start OpenTherm connection."""
        try:
            self.protocol.connect()
            self.connected = True
            logger.info("OpenTherm controller started")
        except Exception as e:
            logger.error(f"Failed to start OpenTherm controller: {e}")
            self.connected = False
    
    def stop(self):
        """Stop OpenTherm connection."""
        if self.connected:
            self.protocol.disconnect()
            self.connected = False
            logger.info("OpenTherm controller stopped")
    
    def set_control_temperature(self, target_temp: float, current_temp: float):
        """Set control temperature based on room with highest difference."""
        if not self.connected:
            logger.warning("OpenTherm not connected, cannot set temperature")
            return False
        
        # Use the target temperature (room with highest difference)
        return self.protocol.set_target_temperature(target_temp)
    
    def get_boiler_status(self) -> Optional[dict]:
        """Get boiler status."""
        if not self.connected:
            return None
        
        temp = self.protocol.get_boiler_temperature()
        status = self.protocol.get_status()
        
        if status:
            status['temperature'] = temp
        return status