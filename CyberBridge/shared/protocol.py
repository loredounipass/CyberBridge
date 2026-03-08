"""
CyberBridge - Shared Protocol Definitions
Defines message types and packet structure shared between client and server.
(HTTP transport version — no RPyC dependency)
"""

import time
import uuid


# ─── Message Types ────────────────────────────────────────────────────────────

class MessageType:
    PING            = "ping"
    TERMINAL_CMD    = "execute_command"
    TERMINAL_RESP   = "terminal_resp"
    AUDIO_STREAM    = "get_audio_chunk"
    CAMERA_FRAME    = "get_camera_frame"
    SCREEN_FRAME    = "screen_frame"
    SCREENSHOT      = "screenshot"
    HEARTBEAT       = "heartbeat"
    SYSTEM_INFO     = "get_system_info"
    FILE_LIST       = "list_directory"
    FILE_TRANSFER   = "file_transfer"
    START_AUDIO     = "start_audio_stream"
    STOP_AUDIO      = "stop_audio_stream"
    START_AUDIO_REC = "start_audio_record"
    STOP_AUDIO_REC  = "stop_audio_record"
    DISCONNECT      = "disconnect"


# ─── Packet Structure ─────────────────────────────────────────────────────────

class Packet:
    """
    Base communication packet used for all HTTP messages.
    """
    def __init__(self, msg_type: str, payload: dict = None):
        self.id        = str(uuid.uuid4())
        self.type      = msg_type
        self.payload   = payload or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "type":      self.type,
            "payload":   self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Packet":
        pkt           = cls(data["type"], data.get("payload", {}))
        pkt.id        = data.get("id", pkt.id)
        pkt.timestamp = data.get("timestamp", pkt.timestamp)
        return pkt
