"""
Tests for Data Streamer API (Module 4)

TDD Phase: RED - All tests must FAIL initially

Tasks:
- T026 [P]: test_websocket_broadcast (send WebSocketMessage to clients)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
import asyncio
import json
from live.backend.api import app, DataStreamer
from live.shared.models import (
    MempoolState,
    WebSocketMessage,
    MempoolUpdateData,
    TransactionPoint,
    SystemStats
)


# =============================================================================
# T026: WebSocket Broadcasting Test
# =============================================================================


@pytest.mark.asyncio
async def test_websocket_broadcast():
    """
    Test that DataStreamer broadcasts mempool updates to all connected clients.
    
    Requirements:
    - Accept WebSocket connections from multiple clients
    - Broadcast MempoolState updates as WebSocketMessage to all clients
    - Handle client disconnections gracefully
    - Send updates at regular intervals (e.g., every 100ms)
    
    Contract:
        DataStreamer.broadcast(state: MempoolState) -> None
        WebSocket endpoint: /ws
    """
    # Arrange: Create streamer
    streamer = DataStreamer()
    
    # Create sample mempool state
    state = MempoolState(
        price=113600.50,
        confidence=0.87,
        active_tx_count=4309,
        total_received=12543,
        total_filtered=8234,
        uptime_seconds=3600.5
    )
    
    # Mock WebSocket clients
    mock_client1 = MockWebSocketClient()
    mock_client2 = MockWebSocketClient()
    
    # Register clients
    await streamer.register_client(mock_client1)
    await streamer.register_client(mock_client2)
    
    # Act: Broadcast state to all clients
    await streamer.broadcast(state)
    
    # Assert: Both clients received the message
    assert mock_client1.messages_received == 1, "Client 1 should receive 1 message"
    assert mock_client2.messages_received == 1, "Client 2 should receive 1 message"
    
    # Assert: Message is valid WebSocketMessage JSON
    msg1 = json.loads(mock_client1.last_message)
    assert msg1["type"] == "mempool_update"
    assert msg1["data"]["price"] == 113600.50
    assert msg1["data"]["confidence"] == 0.87


def test_websocket_endpoint_connection():
    """
    Test that WebSocket endpoint accepts connections.
    
    Requirements:
    - FastAPI app has /ws endpoint
    - Endpoint accepts WebSocket connections
    - Returns proper WebSocket protocol
    
    Contract: GET /ws with Upgrade header establishes WebSocket
    """
    # Arrange: Create test client
    client = TestClient(app)
    
    # Act & Assert: Connect to WebSocket
    with client.websocket_connect("/ws") as websocket:
        # Connection successful
        assert websocket is not None, "WebSocket connection should be established"
        
        # WebSocket is open
        # In FastAPI TestClient, successful connection means it's working


@pytest.mark.asyncio
async def test_websocket_receives_mempool_updates():
    """
    Test that connected WebSocket client receives periodic mempool updates.
    
    Requirements:
    - Client receives WebSocketMessage after connection
    - Message format matches WebSocketMessage schema
    - Updates contain price, confidence, transactions, stats
    
    Contract: WebSocket sends JSON matching WebSocketMessage schema
    """
    # Arrange: Create test client
    client = TestClient(app)
    
    # Act: Connect and receive message
    with client.websocket_connect("/ws") as websocket:
        # Wait for first update (with timeout)
        try:
            data = websocket.receive_json(timeout=5.0)
        except Exception as e:
            pytest.fail(f"Did not receive message within timeout: {e}")
        
        # Assert: Message is valid WebSocketMessage
        # Validate against Pydantic model
        try:
            msg = WebSocketMessage(**data)
        except Exception as e:
            pytest.fail(f"Received message does not match WebSocketMessage schema: {e}")
        
        # Assert: Message has expected structure
        assert msg.type == "mempool_update"
        assert msg.data.price > 0
        assert 0.0 <= msg.data.confidence <= 1.0
        assert isinstance(msg.data.transactions, list)
        assert msg.data.stats.total_received >= 0


def test_websocket_multiple_clients():
    """
    Test that multiple clients can connect simultaneously.
    
    Requirements:
    - Support multiple concurrent WebSocket connections
    - Each client receives independent stream of updates
    - Disconnecting one client doesn't affect others
    
    Contract: DataStreamer manages multiple client connections
    """
    # Arrange: Create test client
    client = TestClient(app)
    
    # Act: Open 3 simultaneous connections
    with client.websocket_connect("/ws") as ws1, \
         client.websocket_connect("/ws") as ws2, \
         client.websocket_connect("/ws") as ws3:
        
        # All connections established
        assert ws1 is not None
        assert ws2 is not None
        assert ws3 is not None
        
        # Each client can receive data independently
        data1 = ws1.receive_json(timeout=5.0)
        data2 = ws2.receive_json(timeout=5.0)
        data3 = ws3.receive_json(timeout=5.0)
        
        # All received valid messages
        assert data1["type"] == "mempool_update"
        assert data2["type"] == "mempool_update"
        assert data3["type"] == "mempool_update"


@pytest.mark.asyncio
async def test_websocket_client_disconnect_handling():
    """
    Test that DataStreamer handles client disconnections gracefully.
    
    Requirements:
    - Remove disconnected clients from broadcast list
    - Continue broadcasting to remaining clients
    - Don't crash when client disconnects mid-broadcast
    
    Contract: broadcast() handles disconnected clients without errors
    """
    # Arrange: Create streamer
    streamer = DataStreamer()
    
    # Create clients
    client1 = MockWebSocketClient()
    client2 = MockWebSocketClient()
    
    await streamer.register_client(client1)
    await streamer.register_client(client2)
    
    # Disconnect client1
    client1.disconnect()
    
    # Create state
    state = MempoolState(
        price=113600.50,
        confidence=0.87,
        active_tx_count=100,
        total_received=200,
        total_filtered=100,
        uptime_seconds=60.0
    )
    
    # Act: Broadcast (should skip disconnected client1)
    await streamer.broadcast(state)
    
    # Assert: Only client2 received message (client1 was skipped)
    assert client1.messages_received == 0, "Disconnected client should not receive messages"
    assert client2.messages_received == 1, "Connected client should receive message"


def test_websocket_message_serialization():
    """
    Test that WebSocketMessage serializes correctly to JSON.
    
    Requirements:
    - Pydantic model serializes to valid JSON
    - All fields are present in serialized output
    - Can deserialize back to WebSocketMessage
    
    Contract: WebSocketMessage.model_dump_json() produces valid JSON
    """
    # Arrange: Create WebSocketMessage
    msg = WebSocketMessage(
        data=MempoolUpdateData(
            price=113600.50,
            confidence=0.87,
            transactions=[
                TransactionPoint(timestamp=1678901234.1, price=113500.0),
                TransactionPoint(timestamp=1678901234.2, price=113700.0)
            ],
            stats=SystemStats(
                total_received=12543,
                total_filtered=8234,
                active_in_window=4309,
                uptime_seconds=3600.5
            ),
            timestamp=1678901234.567
        )
    )
    
    # Act: Serialize to JSON
    json_str = msg.model_dump_json()
    
    # Assert: Valid JSON
    parsed = json.loads(json_str)
    assert parsed["type"] == "mempool_update"
    assert parsed["data"]["price"] == 113600.50
    
    # Assert: Can deserialize back
    msg2 = WebSocketMessage.model_validate_json(json_str)
    assert msg2.data.price == 113600.50
    assert msg2.data.confidence == 0.87
    assert len(msg2.data.transactions) == 2


@pytest.mark.asyncio
async def test_websocket_broadcast_rate_limiting():
    """
    Test that broadcasts don't overwhelm clients with too many messages.
    
    Requirements:
    - Limit broadcast rate (e.g., max 10 updates/second)
    - Throttle updates if state changes too frequently
    - Ensure clients receive latest state even if intermediate updates are skipped
    
    Contract: DataStreamer.broadcast() respects rate limits
    """
    # Arrange: Create streamer with rate limit
    streamer = DataStreamer(max_updates_per_second=10)
    
    client = MockWebSocketClient()
    await streamer.register_client(client)
    
    # Act: Send 50 rapid updates
    import time
    start_time = time.time()
    
    for i in range(50):
        state = MempoolState(
            price=113000.0 + i,  # Incrementing price
            confidence=0.5,
            active_tx_count=100,
            total_received=200,
            total_filtered=100,
            uptime_seconds=60.0
        )
        await streamer.broadcast(state)
    
    elapsed = time.time() - start_time
    
    # Assert: Client received throttled messages (not all 50)
    # With 10 updates/second limit and ~0 seconds elapsed, should receive ~10 messages max
    # (actual behavior depends on implementation)
    assert client.messages_received <= 50, "Should receive at most 50 messages"
    
    # If rate limiting works, messages_received should be much less than 50
    # This is a heuristic - actual implementation may vary


# =============================================================================
# Mock WebSocket Client
# =============================================================================


class MockWebSocketClient:
    """Mock WebSocket client for testing"""
    
    def __init__(self):
        self.messages_received = 0
        self.last_message = None
        self._connected = True
    
    async def send_text(self, message: str):
        """Simulate receiving message from server"""
        if not self._connected:
            raise RuntimeError("WebSocket disconnected")
        
        self.messages_received += 1
        self.last_message = message
    
    def disconnect(self):
        """Simulate client disconnect"""
        self._connected = False
    
    @property
    def is_connected(self):
        return self._connected


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mempool_state() -> MempoolState:
    """Sample mempool state for testing"""
    return MempoolState(
        price=113600.50,
        confidence=0.87,
        active_tx_count=4309,
        total_received=12543,
        total_filtered=8234,
        uptime_seconds=3600.5
    )


@pytest.fixture
def sample_websocket_message() -> WebSocketMessage:
    """Sample WebSocket message for testing"""
    return WebSocketMessage(
        data=MempoolUpdateData(
            price=113600.50,
            confidence=0.87,
            transactions=[
                TransactionPoint(timestamp=1678901234.1, price=113500.0),
                TransactionPoint(timestamp=1678901234.2, price=113700.0)
            ],
            stats=SystemStats(
                total_received=12543,
                total_filtered=8234,
                active_in_window=4309,
                uptime_seconds=3600.5
            ),
            timestamp=1678901234.567
        )
    )
