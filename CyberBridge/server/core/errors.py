"""
CyberBridge - Professional Error Handling
Defines a strict hierarchy of exceptions for the server architecture.
"""

class CyberBridgeError(Exception):
    """Base exception class for all CyberBridge related errors."""
    pass

class ProtocolError(CyberBridgeError):
    """Base exception for protocol-related errors."""
    pass

class ProtocolNotSupportedError(ProtocolError):
    """Raised when an attempt is made to initialize a protocol that is not supported or not implemented."""
    def __init__(self, protocol: str):
        self.protocol = protocol
        super().__init__(f"The protocol '{protocol}' is not currently supported or implemented.")

class ProtocolConfigurationError(ProtocolError):
    """Raised when there is an error in the configuration of a specific protocol."""
    pass

class NetworkBindError(CyberBridgeError):
    """Raised when the server fails to bind to a specific network interface or port."""
    def __init__(self, port: int, protocol: str, original_error: Exception = None):
        self.port = port
        self.protocol = protocol
        self.original_error = original_error
        msg = f"Failed to bind {protocol} server to port {port}."
        if original_error:
            msg += f" Details: {str(original_error)}"
        super().__init__(msg)
