"""Trading workflow state machine."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TradingState(Enum):
    IDLE            = auto()
    SCANNING        = auto()
    SIGNAL_FOUND    = auto()
    RISK_VALIDATING = auto()
    ORDER_PENDING   = auto()
    POSITION_OPEN   = auto()
    EXIT_PENDING    = auto()
    POSITION_CLOSED = auto()
    ERROR           = auto()
    STOPPED         = auto()


class TradingEvent(Enum):
    MARKET_OPEN         = auto()
    MARKET_CLOSE        = auto()
    SCAN_COMPLETE       = auto()
    SIGNAL_VALID        = auto()
    RISK_APPROVED       = auto()
    RISK_REJECTED       = auto()
    ORDER_PLACED        = auto()
    ORDER_FAILED        = auto()
    POSITION_CONFIRMED  = auto()
    EXIT_SIGNAL         = auto()
    EXIT_ORDER_PLACED   = auto()
    EXIT_COMPLETED      = auto()
    ERROR_OCCURRED      = auto()
    STOP_REQUESTED      = auto()


@dataclass
class StateTransition:
    from_state: TradingState
    to_state: TradingState
    event: TradingEvent
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


class TradingStateMachine:
    TRANSITIONS: Dict[TradingState, Dict[TradingEvent, TradingState]] = {
        TradingState.IDLE:            {TradingEvent.MARKET_OPEN: TradingState.SCANNING,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.SCANNING:        {TradingEvent.SCAN_COMPLETE: TradingState.IDLE,
                                        TradingEvent.SIGNAL_VALID: TradingState.SIGNAL_FOUND,
                                        TradingEvent.MARKET_CLOSE: TradingState.IDLE,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.SIGNAL_FOUND:    {TradingEvent.RISK_APPROVED: TradingState.RISK_VALIDATING,
                                        TradingEvent.RISK_REJECTED: TradingState.SCANNING,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.RISK_VALIDATING: {TradingEvent.RISK_APPROVED: TradingState.ORDER_PENDING,
                                        TradingEvent.RISK_REJECTED: TradingState.SCANNING,
                                        TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.ORDER_PENDING:   {TradingEvent.POSITION_CONFIRMED: TradingState.POSITION_OPEN,
                                        TradingEvent.ORDER_FAILED: TradingState.SCANNING,
                                        TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.POSITION_OPEN:   {TradingEvent.EXIT_SIGNAL: TradingState.EXIT_PENDING,
                                        TradingEvent.MARKET_CLOSE: TradingState.EXIT_PENDING,
                                        TradingEvent.ERROR_OCCURRED: TradingState.ERROR,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.EXIT_PENDING:    {TradingEvent.EXIT_COMPLETED: TradingState.POSITION_CLOSED,
                                        TradingEvent.ERROR_OCCURRED: TradingState.ERROR},
        TradingState.POSITION_CLOSED: {TradingEvent.SCAN_COMPLETE: TradingState.SCANNING,
                                        TradingEvent.MARKET_CLOSE: TradingState.IDLE,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.ERROR:           {TradingEvent.SCAN_COMPLETE: TradingState.SCANNING,
                                        TradingEvent.STOP_REQUESTED: TradingState.STOPPED},
        TradingState.STOPPED:         {TradingEvent.MARKET_OPEN: TradingState.IDLE},
    }

    def __init__(self, initial_state: TradingState = TradingState.IDLE):
        self.state = initial_state
        self.history: List[StateTransition] = []
        self._callbacks: Dict[TradingState, List[Callable]] = {}
        self._transition_callbacks: Dict[tuple, List[Callable]] = {}
        logger.info("StateMachine initialised: %s", initial_state.name)

    def transition(self, event: TradingEvent, data: Optional[Dict] = None) -> bool:
        valid = self.TRANSITIONS.get(self.state, {})
        if event not in valid:
            return False
        old = self.state
        self.state = valid[event]
        t = StateTransition(old, self.state, event, data=data or {})
        self.history.append(t)
        self._fire(self.state, t)
        logger.debug("%s --%s--> %s", old.name, event.name, self.state.name)
        return True

    def transition_to(self, new_state: TradingState, data: Optional[Dict] = None) -> bool:
        old = self.state
        self.state = new_state
        t = StateTransition(old, new_state, TradingEvent.SCAN_COMPLETE, data=data or {})
        self.history.append(t)
        self._fire(new_state, t)
        logger.debug("Direct: %s --> %s", old.name, new_state.name)
        return True

    def _fire(self, state: TradingState, transition: StateTransition):
        for cb in self._callbacks.get(state, []):
            try:
                cb(transition)
            except Exception:
                logger.exception("Callback error for state %s", state.name)
        for cb in self._transition_callbacks.get((transition.from_state, transition.to_state), []):
            try:
                cb(transition)
            except Exception:
                logger.exception("Transition callback error")

    def on_state_change(self, state: TradingState, callback: Callable):
        self._callbacks.setdefault(state, []).append(callback)

    def on_transition(self, from_state: TradingState, to_state: TradingState, callback: Callable):
        self._transition_callbacks.setdefault((from_state, to_state), []).append(callback)

    def get_state(self) -> TradingState:
        return self.state

    def get_state_name(self) -> str:
        return self.state.name

    def can_transition(self, event: TradingEvent) -> bool:
        return event in self.TRANSITIONS.get(self.state, {})

    def reset(self, new_state: TradingState = TradingState.IDLE):
        self.state = new_state
        self.history.clear()
