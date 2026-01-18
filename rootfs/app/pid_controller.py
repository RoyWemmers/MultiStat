"""
PID controller for HRV valve position control.
"""
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PIDController:
    """PID controller for HRV valve position."""
    
    def __init__(self, kp: float = 1.0, ki: float = 0.1, kd: float = 0.05, 
                 setpoint: float = 0.0, output_limits: tuple = (0.0, 100.0)):
        """
        Initialize PID controller.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            setpoint: Target value
            output_limits: Tuple of (min, max) output values
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        self._last_time: Optional[float] = None
        self._last_error: Optional[float] = None
        self._integral = 0.0
        
    def set_setpoint(self, setpoint: float):
        """Set the target setpoint."""
        self.setpoint = setpoint
        # Reset integral when setpoint changes
        self._integral = 0.0
    
    def update(self, current_value: float) -> float:
        """
        Calculate PID output based on current value.
        
        Args:
            current_value: Current measured value
            
        Returns:
            PID output value (clamped to output_limits)
        """
        current_time = time.time()
        error = self.setpoint - current_value
        
        # Initialize on first call
        if self._last_time is None:
            self._last_time = current_time
            self._last_error = error
            return self._clamp_output(self.kp * error)
        
        # Calculate time delta
        dt = current_time - self._last_time
        if dt <= 0:
            return self._clamp_output(self.kp * error)
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self._integral += error * dt
        i_term = self.ki * self._integral
        
        # Derivative term
        error_delta = error - self._last_error
        d_term = self.kd * (error_delta / dt)
        
        # Calculate output
        output = p_term + i_term + d_term
        
        # Update state
        self._last_time = current_time
        self._last_error = error
        
        return self._clamp_output(output)
    
    def _clamp_output(self, output: float) -> float:
        """Clamp output to specified limits."""
        return max(self.output_limits[0], min(self.output_limits[1], output))
    
    def reset(self):
        """Reset PID controller state."""
        self._last_time = None
        self._last_error = None
        self._integral = 0.0
        logger.debug("PID controller reset")
    
    def set_tunings(self, kp: float, ki: float, kd: float):
        """Update PID tuning parameters."""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        logger.info(f"PID tunings updated: Kp={kp}, Ki={ki}, Kd={kd}")