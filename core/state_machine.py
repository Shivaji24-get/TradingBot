"""
Trading State Machine - State management for trading workflow.

Manages the state of trading operations:
- IDLE → SCANNING → SIGNAL_FOUND → ORDER_PENDING → POSITION_OPEN → EXIT_PENDING → POSITION_CLOSED

Inspired by Career-Ops workflow state management patterns.
"""

import logging
from typing import Optional, Callable, Dict, List, Any
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingState(Enum):
    """Trading workflow states."""
    IDLE = auto()              # Waiting for market open/session
    SCANNING = auto()          # Analyzing market data
    SIGNAL_FOUND = auto()      # Valid signal detected
    RISK_VALIDATING = auto()   # Checking risk parameters
    ORDER_PENDING = auto()     # Order submitted
    POSITION_OPEN = auto()     # Active position
    EXIT_PENDING = auto()      # Exit order submitted
    POSITION_CLOSED = auto()   # Trade completed
    ERROR = auto()             # Error state
    STOPPED = auto()           # Trading stopped


class TradingEvent(Enum):
    """Events that can trigger state transitions."""
    MARKET_OPEN = auto()
    MARKET_CLOSE = auto()
    SCAN_COMPLETE = auto()
    SIGNAL_VALID = auto()
    RISK_APPROVED = auto()
    RISK_REJECTED = auto()
    ORDER_PLACED = auto()
    ORDER_FAILED = auto()
    POSITION_CONFIRMED = auto()
    EXIT_SIGNAL = auto()
    EXIT_ORDER_PLACED = auto()
    EXIT_COMPLETED = auto()
    ERROR_OCCURRED = auto()
    STOP_REQUESTED = auto()


@dataclass
class StateTransition:
    """Represents a state transition."""
    from_state: TradingState
    to_state: TradingState
    event: TradingEvent
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


class TradingStateMachine:
    """
    State machine for trading workflow.
    
    Manages state transitions and callbacks for the trading process.
    
    State Flow:
        IDLE → SCANNING → SIGNAL_FOUND → RISK_VALIDATING → ORDER_PENDING → 
        POSITION_OPEN → [EXIT_SIGNAL] → EXIT_PENDING → POSITION_CLOSED → IDLE
    
    Usage:
        sm = TradingStateMachine()
        sm.on_state_change(TradingState.POSITION_OPEN, on_position_opened)
        sm.transition(TradingEvent.MARKET_OPEN)
    """
    
    # Valid state transitions
    TRANSITIONS: Dict[TradingState, Dict[TradingEvent, TradingState]] = {
        TradingState.IDLE: {
            TradingEvent.MARKET_OPEN: TradingState.SCANNING,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.SCANNING: {
            TradingEvent.SCAN_COMPLETE: TradingState.IDLE,
            TradingEvent.SIGNAL_VALID: TradingState.SIGNAL_FOUND,
            TradingEvent.MARKET_CLOSE: TradingState.IDLE,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.SIGNAL_FOUND: {
            TradingEvent.RISK_APPROVED: TradingState.RISK_VALIDATING,
            TradingEvent.RISK_REJECTED: TradingState.SCANNING,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.RISK_VALIDATING: {
            TradingEvent.RISK_APPROVED: TradingState.ORDER_PENDING,
            TradingEvent.RISK_REJECTED: TradingState.SCANNING,
            TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.ORDER_PENDING: {
            TradingEvent.POSITION_CONFIRMED: TradingState.POSITION_OPEN,
            TradingEvent.ORDER_FAILED: TradingState.SCANNING,
            TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.POSITION_OPEN: {
            TradingEvent.EXIT_SIGNAL: TradingState.EXIT_PENDING,
            TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
            TradingEvent.MARKET_CLOSE: TradingState.EXIT_PENDING,
        },
        TradingState.EXIT_PENDING: {
            TradingEvent.EXIT_COMPLETED: TradingState.POSITION_CLOSED,
            TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
        },
        TradingState.POSITION_CLOSED: {
            TradingEvent.SCAN_COMPLETE: TradingState.SCANNING,
            TradingEvent.MARKET_CLOSE: TradingState.IDLE,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.ERROR: {
            TradingEvent.SCAN_COMPLETE: TradingState.SCANNING,
            TradingEvent.STOP_REQUESTED: TradingState.STOPPED,
        },
        TradingState.STOPPED: {
            TradingEvent.MARKET_OPEN: TradingState.IDLE,
        },
    }
    
    def __init__(self, initial_state: TradingState = TradingState.IDLE):
        self.state = initial_state
        self.history: List[StateTransition] = []
        self._callbacks: Dict[TradingState, List[Callable]] = {}
        self._transition_callbacks: Dict[tuple, List[Callable]] = {}
        
        self._record_transition(None, initial_state, None)
        
        logger.info(f"TradingStateMachine initialized in {initial_state.name}")
    
    def transition(self, event: TradingEvent, data: Optional[Dict] = None) -> bool:
        """
        Trigger a state transition.
        
        Args:
            event: The event triggering the transition
            data: Optional data associated with the transition
            
        Returns:
            True if transition was successful
        """
        if self.state not in self.TRANSITIONS:
            logger.warning(f"No transitions defined for state {self.state.name}")
            return False
        
        valid_transitions = self.TRANSITIONS[self.state]
        
        if event not in valid_transitions:
            logger.debug(
                f"Event {event.name} not valid from state {self.state.name}"
            )
            return False
        
        new_state = valid_transitions[event]
        
        # Perform transition
        old_state = self.state
        self.state = new_state
        
        # Record transition
        transition = self._record_transition(old_state, new_state, event, data)
        
        # Trigger callbacks
        self._trigger_callbacks(new_state, transition)
        
        logger.info(
            f"State transition: {old_state.name} --{event.name}--> {new_state.name}"
        )
        
        return True
    
    def _record_transition(
        self,
        from_state: Optional[TradingState],
        to_state: TradingState,
        event: Optional[TradingEvent],
        data: Optional[Dict] = None
    ) -> StateTransition:
        """Record a state transition."""
        transition = StateTransition(
            from_state=from_state or TradingState.IDLE,
            to_state=to_state,
            event=event or TradingEvent.SCAN_COMPLETE,
            data=data or {}
        )
        self.history.append(transition)
        return transition
    
    def _trigger_callbacks(self, state: TradingState, transition: StateTransition):
        """Trigger registered callbacks."""
        # State-specific callbacks
        if state in self._callbacks:
            for callback in self._callbacks[state]:
                try:
                    callback(transition)
                except Exception as e:
                    logger.error(f"Callback error for state {state.name}: {e}")
        
        # Transition-specific callbacks
        key = (transition.from_state, transition.to_state)
        if key in self._transition_callbacks:
            for callback in self._transition_callbacks[key]:
                try:
                    callback(transition)
                except Exception as e:
                    logger.error(f"Callback error for transition {key}: {e}")
    
    def on_state_change(
        self,
        state: TradingState,
        callback: Callable[[StateTransition], None]
    ):
        """
        Register a callback for a specific state.
        
        Args:
            state: State to watch
            callback: Function to call when entering this state
        """
        if state not in self._callbacks:
            self._callbacks[state] = []
        self._callbacks[state].append(callback)
    
    def on_transition(
        self,
        from_state: TradingState,
        to_state: TradingState,
        callback: Callable[[StateTransition], None]
    ):
        """
        Register a callback for a specific transition.
        
        Args:
            from_state: Source state
            to_state: Destination state
            callback: Function to call for this transition
        """
        key = (from_state, to_state)
        if key not in self._transition_callbacks:
            self._transition_callbacks[key] = []
        self._transition_callbacks[key].append(callback)
    
    def transition_to(self, new_state: TradingState, data: Optional[Dict] = None) -> bool:
        """
        Direct transition to a specific state (bypasses event-based transitions).
        
        Args:
            new_state: Target state
            data: Optional data for the transition
            
        Returns:
            True if transition was successful
        """
        old_state = self.state
        self.state = new_state
        
        # Record the transition
        transition = self._record_transition(old_state, new_state, None, data)
        
        # Trigger callbacks
        self._trigger_callbacks(new_state, transition)
        
        logger.info(f"Direct state transition: {old_state.name} --> {new_state.name}")
        return True
    
    def get_state(self) -> TradingState:
        """Get current state."""
        return self.state
    
    def get_state_name(self) -> str:
        """Get current state name."""
        return self.state.name
    
    def get_history(self) -> List[StateTransition]:
        """Get state transition history."""
        return self.history.copy()
    
    def is_in_state(self, state: TradingState) -> bool:
        """Check if currently in a specific state."""
        return self.state == state
    
    def can_transition(self, event: TradingEvent) -> bool:
        """Check if a transition is possible."""
        if self.state not in self.TRANSITIONS:
            return False
        return event in self.TRANSITIONS[self.state]
    
    def get_valid_events(self) -> List[TradingEvent]:
        """Get list of valid events from current state."""
        if self.state not in self.TRANSITIONS:
            return []
        return list(self.TRANSITIONS[self.state].keys())
    
    def reset(self, new_state: TradingState = TradingState.IDLE):
        """Reset state machine to initial state."""
        old_state = self.state
        self.state = new_state
        self.history.clear()
        self._record_transition(None, new_state, None)
        logger.info(f"State machine reset: {old_state.name} -> {new_state.name}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get state machine summary."""
        # Count time in each state
        state_times: Dict[str, float] = {}
        
        for i, transition in enumerate(self.history):
            if i > 0:
                prev_transition = self.history[i - 1]
                duration = (
                    transition.timestamp - prev_transition.timestamp
                ).total_seconds()
                state_name = prev_transition.to_state.name
                state_times[state_name] = state_times.get(state_name, 0) + duration
        
        return {
            'current_state': self.state.name,
            'transitions_count': len(self.history) - 1,  # Exclude initial
            'time_in_states': state_times,
            'recent_transitions': [
                {
                    'from': t.from_state.name,
                    'to': t.to_state.name,
                    'event': t.event.name,
                    'time': t.timestamp.strftime('%H:%M:%S')
                }
                for t in self.history[-5:]  # Last 5
            ]
        }
