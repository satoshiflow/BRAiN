# BRAiN Plugin System

**Version:** 1.0.0
**Created:** 2025-12-20
**Phase:** 5 - Developer Experience & Advanced Features

## Overview

The BRAiN Plugin System provides an extensible architecture for adding custom functionality without modifying core code. The system supports multiple plugin types, automatic discovery, lifecycle management, and a powerful hook system.

### Key Features

- ✅ **Multiple Plugin Types** - Agent, Mission, API, Middleware, Event Listener, Generic
- ✅ **Automatic Discovery** - Scan directories for plugin files
- ✅ **Lifecycle Management** - Load, enable, disable, unload plugins
- ✅ **Hot Reload** - Update plugins without restarting
- ✅ **Hook System** - Extend core functionality with callbacks
- ✅ **Configuration** - JSON schema-based plugin configuration
- ✅ **Validation** - Automatic plugin structure validation
- ✅ **REST API** - Manage plugins via HTTP endpoints
- ✅ **Type Safety** - Full type hints and Pydantic models

## Table of Contents

1. [Architecture](#architecture)
2. [Plugin Types](#plugin-types)
3. [Creating Plugins](#creating-plugins)
4. [Plugin Lifecycle](#plugin-lifecycle)
5. [Hook System](#hook-system)
6. [API Reference](#api-reference)
7. [Examples](#examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Architecture

### System Components

```
Plugin System
├── PluginManager      # Central management and coordination
├── PluginLoader       # Discovery and loading from filesystem
├── PluginRegistry     # Track registered plugins
├── BasePlugin         # Abstract base class for all plugins
├── Specialized Types  # AgentPlugin, APIPlugin, etc.
└── Hook System        # Event-driven extensibility
```

### Plugin Lifecycle States

```
┌──────────┐
│ LOADED   │ ← Plugin loaded into memory
└────┬─────┘
     │
     ▼
┌──────────┐
│ ENABLED  │ ← Plugin active and functional
└────┬─────┘
     │
     ▼
┌──────────┐
│ DISABLED │ ← Plugin inactive but still loaded
└────┬─────┘
     │
     ▼
┌──────────┐
│ ERROR    │ ← Plugin encountered error
└──────────┘
```

### Directory Structure

```
backend/app/plugins/
├── __init__.py              # Package exports
├── base.py                  # Base plugin classes
├── manager.py               # Plugin manager
├── loader.py                # Plugin loader
├── registry.py              # Plugin registry
├── schemas.py               # API models
└── examples/                # Example plugins
    ├── hello_plugin.py
    ├── custom_agent_plugin.py
    └── custom_api_plugin.py
```

---

## Plugin Types

### 1. AgentPlugin

Add custom agents to BRAiN.

**Use Cases:**
- Custom AI agents with specialized capabilities
- Integration with external AI services
- Domain-specific problem solvers

**Required Methods:**
- `create_agent()` - Create agent instance
- `get_agent_capabilities()` - List agent capabilities

**Example:**
```python
class DataAnalystPlugin(AgentPlugin):
    def create_agent(self):
        return CustomDataAnalystAgent(self.config)

    def get_agent_capabilities(self):
        return ["data_analysis", "trend_detection"]
```

### 2. MissionTypePlugin

Add custom mission type handlers.

**Use Cases:**
- Specialized mission execution logic
- Custom mission validation
- Domain-specific workflows

**Required Methods:**
- `get_mission_type()` - Return mission type identifier
- `execute_mission(mission)` - Execute mission logic
- `validate_mission_payload(payload)` - Validate mission data

**Example:**
```python
class DataProcessingMissionPlugin(MissionTypePlugin):
    def get_mission_type(self):
        return "data_processing"

    async def execute_mission(self, mission):
        # Execute data processing logic
        return {"status": "processed"}

    def validate_mission_payload(self, payload):
        return "data_source" in payload
```

### 3. APIPlugin

Add custom API endpoints to BRAiN.

**Use Cases:**
- Custom REST endpoints
- External service integrations
- Specialized business logic APIs

**Required Methods:**
- `get_router()` - Return FastAPI router
- `get_prefix()` - Return URL prefix (e.g., "/api/custom")

**Example:**
```python
class CalculatorAPIPlugin(APIPlugin):
    def get_router(self):
        router = APIRouter()

        @router.post("/calculate")
        async def calculate(a: int, b: int):
            return {"result": a + b}

        return router

    def get_prefix(self):
        return "/api/calculator"
```

### 4. MiddlewarePlugin

Add request/response middleware.

**Use Cases:**
- Request authentication/authorization
- Response transformation
- Logging and monitoring
- Rate limiting

**Required Methods:**
- `process_request(request)` - Process incoming request
- `process_response(request, response)` - Process outgoing response

**Example:**
```python
class LoggingMiddlewarePlugin(MiddlewarePlugin):
    async def process_request(self, request):
        logger.info(f"Request: {request.method} {request.url}")
        return None  # Continue to next middleware

    async def process_response(self, request, response):
        logger.info(f"Response: {response.status_code}")
        return response
```

### 5. EventListenerPlugin

React to system events.

**Use Cases:**
- Event-driven automation
- System monitoring
- Audit logging
- Notifications

**Required Methods:**
- `get_event_subscriptions()` - List of events to subscribe to
- `on_event(event_type, event_data)` - Handle event

**Example:**
```python
class MissionMonitorPlugin(EventListenerPlugin):
    def get_event_subscriptions(self):
        return ["mission_created", "mission_completed", "mission_failed"]

    async def on_event(self, event_type, event_data):
        if event_type == "mission_failed":
            # Send alert
            await send_alert(event_data)
```

### 6. GenericPlugin

General-purpose plugins.

**Use Cases:**
- Utilities that don't fit other categories
- Background tasks
- Data processing
- System maintenance

**Required Methods:**
- `execute(*args, **kwargs)` - Main plugin execution

**Example:**
```python
class DatabaseCleanupPlugin(GenericPlugin):
    async def execute(self):
        # Perform cleanup
        deleted = await cleanup_old_records()
        return {"deleted_count": deleted}
```

---

## Creating Plugins

### Basic Plugin Structure

Every plugin must:
1. Inherit from a plugin base class
2. Implement required abstract methods
3. Provide metadata via `get_metadata()`
4. Implement lifecycle hooks

### Minimal Plugin Example

```python
from backend.app.plugins.base import GenericPlugin, PluginMetadata, PluginType

class HelloPlugin(GenericPlugin):
    """Simple hello world plugin."""

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id="hello_plugin",
            name="Hello Plugin",
            version="1.0.0",
            description="Simple greeting plugin",
            author="Your Name",
            plugin_type=PluginType.GENERIC,
            dependencies=[],
        )

    async def on_load(self):
        """Called when plugin is loaded."""
        print(f"Plugin loaded: {self.config}")

    async def on_enable(self):
        """Called when plugin is enabled."""
        print("Plugin enabled")

    async def on_disable(self):
        """Called when plugin is disabled."""
        print("Plugin disabled")

    async def execute(self, *args, **kwargs):
        """Execute plugin functionality."""
        name = kwargs.get("name", "World")
        return {"message": f"Hello, {name}!"}
```

### Plugin Metadata

```python
PluginMetadata(
    id="unique_plugin_id",              # Required: Unique identifier
    name="Human Readable Name",          # Required: Display name
    version="1.0.0",                     # Required: Semantic version
    description="Plugin description",    # Required: What it does
    author="Author Name",                # Optional: Plugin author
    plugin_type=PluginType.GENERIC,     # Required: Plugin type
    dependencies=[],                     # Optional: Plugin dependencies
    config_schema={                      # Optional: JSON schema for config
        "type": "object",
        "properties": {
            "api_key": {"type": "string"},
            "timeout": {"type": "integer", "default": 30}
        }
    }
)
```

### Configuration

Plugins can access configuration via `self.config`:

```python
class MyPlugin(GenericPlugin):
    async def on_load(self):
        # Get config value with default
        api_key = self.get_config("api_key", "default_key")
        timeout = self.get_config("timeout", 30)

        # Access raw config dict
        print(f"Full config: {self.config}")
```

### Validation

Validate configuration in `on_load()`:

```python
async def on_load(self):
    """Validate configuration."""
    # Check required fields
    if not self.get_config("api_key"):
        raise ValueError("api_key is required")

    # Validate ranges
    timeout = self.get_config("timeout", 30)
    if timeout < 1 or timeout > 300:
        raise ValueError("timeout must be between 1 and 300")

    # Validate types
    if not isinstance(self.get_config("enabled", True), bool):
        raise ValueError("enabled must be a boolean")
```

---

## Plugin Lifecycle

### States and Transitions

**LOADED** → Plugin loaded into memory, configuration validated
- Can transition to: ENABLED
- Cannot be used yet

**ENABLED** → Plugin active and functional
- Can transition to: DISABLED
- Fully functional and integrated

**DISABLED** → Plugin inactive but still in memory
- Can transition to: ENABLED, UNLOADED
- Not functional but can be re-enabled

**ERROR** → Plugin encountered error
- Can transition to: DISABLED, UNLOADED
- Check `get_error()` for error message

### Lifecycle Hooks

#### on_load()

Called when plugin is first loaded into memory.

**Purpose:**
- Validate configuration
- Initialize lightweight resources
- Check dependencies

**Example:**
```python
async def on_load(self):
    """Validate and initialize."""
    # Validate config
    if not self.get_config("api_key"):
        raise ValueError("api_key required")

    # Check dependencies
    try:
        import external_library
    except ImportError:
        raise ValueError("external_library not installed")

    logger.info("Plugin loaded successfully")
```

#### on_enable()

Called when plugin is enabled.

**Purpose:**
- Initialize resources (databases, connections, etc.)
- Start background tasks
- Register handlers
- Set up subscriptions

**Example:**
```python
async def on_enable(self):
    """Start plugin functionality."""
    # Initialize database connection
    self.db = await connect_database(self.get_config("db_url"))

    # Start background task
    self.task = asyncio.create_task(self._background_worker())

    # Register with external service
    await self.service.register(self.get_config("api_key"))

    logger.info("Plugin enabled")
```

#### on_disable()

Called when plugin is disabled.

**Purpose:**
- Stop background tasks
- Close connections
- Unregister handlers
- Cleanup resources

**Example:**
```python
async def on_disable(self):
    """Stop plugin functionality."""
    # Cancel background task
    if hasattr(self, 'task'):
        self.task.cancel()
        await self.task

    # Close database connection
    if hasattr(self, 'db'):
        await self.db.close()

    # Unregister from service
    await self.service.unregister()

    logger.info("Plugin disabled")
```

#### on_unload()

Called when plugin is unloaded from memory.

**Purpose:**
- Final cleanup
- Save state if needed
- Release all resources

**Example:**
```python
async def on_unload(self):
    """Final cleanup."""
    # Save state
    await self.save_state()

    # Release cached data
    self.cache.clear()

    logger.info("Plugin unloaded")
```

### Lifecycle Management

**Programmatic:**
```python
from backend.app.plugins import get_plugin_manager

manager = get_plugin_manager()

# Load plugin
await manager.load_plugin("my_plugin", config={"api_key": "xxx"})

# Enable plugin
await manager.enable_plugin("my_plugin")

# Disable plugin
await manager.disable_plugin("my_plugin")

# Unload plugin
await manager.unload_plugin("my_plugin")
```

**REST API:**
```bash
# Load plugin
curl -X POST http://localhost:8000/api/plugins/load \
  -H "Content-Type: application/json" \
  -d '{"plugin_id": "my_plugin", "config": {"api_key": "xxx"}}'

# Enable plugin
curl -X POST http://localhost:8000/api/plugins/enable \
  -H "Content-Type: application/json" \
  -d '{"plugin_id": "my_plugin"}'

# Disable plugin
curl -X POST http://localhost:8000/api/plugins/disable \
  -H "Content-Type: application/json" \
  -d '{"plugin_id": "my_plugin"}'

# Unload plugin
curl -X POST http://localhost:8000/api/plugins/unload \
  -H "Content-Type: application/json" \
  -d '{"plugin_id": "my_plugin"}'
```

---

## Hook System

### Standard Hooks

The plugin system provides standard hooks for common events:

| Hook Name | Triggered When | Use Case |
|-----------|---------------|----------|
| `app_startup` | Application starts | Initialization tasks |
| `app_shutdown` | Application stops | Cleanup tasks |
| `mission_created` | Mission created | Track missions |
| `mission_completed` | Mission succeeds | Post-processing |
| `agent_started` | Agent starts | Monitoring |
| `agent_stopped` | Agent stops | Cleanup |
| `request_received` | HTTP request received | Logging, auth |
| `response_sent` | HTTP response sent | Metrics |

### Using Hooks

**Register Callback:**
```python
from backend.app.plugins import get_plugin_manager

manager = get_plugin_manager()

# Get hook
hook = manager.get_hook("mission_created")

# Register callback
async def on_mission_created(mission_data):
    logger.info(f"Mission created: {mission_data['mission_id']}")

hook.register(on_mission_created)
```

**Execute Hook:**
```python
# Execute all registered callbacks
results = await manager.execute_hook(
    "mission_created",
    mission_data={"mission_id": "123", "name": "Test"}
)
```

### Custom Hooks

Create custom hooks for plugin-to-plugin communication:

```python
manager = get_plugin_manager()

# Create custom hook
from backend.app.plugins.base import PluginHook
manager.hooks["custom_event"] = PluginHook("custom_event")

# Register callback
manager.hooks["custom_event"].register(my_callback)

# Execute hook
await manager.execute_hook("custom_event", data={"key": "value"})
```

### Event Listener Plugins

Event listener plugins automatically register for hooks:

```python
class MyEventPlugin(EventListenerPlugin):
    def get_event_subscriptions(self):
        """Subscribe to events."""
        return ["mission_created", "mission_completed"]

    async def on_event(self, event_type, event_data):
        """Handle event."""
        if event_type == "mission_created":
            logger.info(f"New mission: {event_data}")
        elif event_type == "mission_completed":
            logger.info(f"Mission done: {event_data}")
```

When enabled, the plugin automatically registers `on_event()` as a callback for specified events.

---

## API Reference

### Plugin Management Endpoints

#### List Plugins

**GET /api/plugins**

List all registered plugins with optional filters.

**Query Parameters:**
- `plugin_type` - Filter by plugin type
- `status_filter` - Filter by status

**Response:**
```json
{
  "plugins": [
    {
      "id": "hello_plugin",
      "name": "Hello Plugin",
      "version": "1.0.0",
      "description": "Simple greeting plugin",
      "author": "BRAiN Team",
      "plugin_type": "generic",
      "status": "enabled",
      "dependencies": [],
      "config_schema": {...},
      "error": null
    }
  ],
  "total": 1
}
```

#### Get Plugin Details

**GET /api/plugins/{plugin_id}**

Get detailed information about specific plugin.

**Response:**
```json
{
  "id": "hello_plugin",
  "name": "Hello Plugin",
  "version": "1.0.0",
  "status": "enabled",
  ...
}
```

#### Load Plugin

**POST /api/plugins/load**

Load plugin into memory.

**Request:**
```json
{
  "plugin_id": "my_plugin",
  "config": {
    "api_key": "xxx",
    "timeout": 30
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Plugin loaded successfully: my_plugin",
  "plugin_id": "my_plugin"
}
```

#### Enable Plugin

**POST /api/plugins/enable**

Enable loaded plugin.

**Request:**
```json
{
  "plugin_id": "my_plugin"
}
```

#### Disable Plugin

**POST /api/plugins/disable**

Disable active plugin.

**Request:**
```json
{
  "plugin_id": "my_plugin"
}
```

#### Unload Plugin

**POST /api/plugins/unload**

Unload plugin from memory.

**Request:**
```json
{
  "plugin_id": "my_plugin"
}
```

#### Get Statistics

**GET /api/plugins/stats**

Get plugin system statistics.

**Response:**
```json
{
  "total": 5,
  "by_status": {
    "loaded": 1,
    "enabled": 3,
    "disabled": 1,
    "error": 0
  },
  "by_type": {
    "agent": 2,
    "api": 1,
    "generic": 2,
    ...
  }
}
```

#### List Hooks

**GET /api/plugins/hooks**

List all registered hooks.

**Response:**
```json
{
  "hooks": [
    {
      "name": "mission_created",
      "callback_count": 3
    },
    {
      "name": "app_startup",
      "callback_count": 1
    }
  ],
  "total": 2
}
```

#### System Info

**GET /api/plugins/info**

Get plugin system information.

**Response:**
```json
{
  "name": "BRAiN Plugin System",
  "version": "1.0.0",
  "plugin_types": ["agent", "mission_type", "api", "middleware", "event_listener", "generic"],
  "total_plugins": 5,
  "enabled_plugins": 3
}
```

### Programmatic API

#### PluginManager

```python
from backend.app.plugins import get_plugin_manager

manager = get_plugin_manager()

# Initialize system
await manager.initialize()

# Load plugin
success = await manager.load_plugin("plugin_id", config={})

# Enable/disable
await manager.enable_plugin("plugin_id")
await manager.disable_plugin("plugin_id")

# Unload plugin
await manager.unload_plugin("plugin_id")

# Query plugins
plugin = manager.get_plugin("plugin_id")
plugins = manager.list_plugins(plugin_type=PluginType.AGENT)
metadata = manager.get_plugin_metadata("plugin_id")

# Hooks
hook = manager.get_hook("mission_created")
results = await manager.execute_hook("mission_created", data={})

# Shutdown
await manager.shutdown()
```

---

## Examples

### Example 1: Hello World Plugin

```python
# plugins/hello_plugin.py
from backend.app.plugins import GenericPlugin, PluginMetadata, PluginType

class HelloPlugin(GenericPlugin):
    def get_metadata(self):
        return PluginMetadata(
            id="hello",
            name="Hello Plugin",
            version="1.0.0",
            description="Greets users",
            plugin_type=PluginType.GENERIC,
        )

    async def on_load(self):
        logger.info("Hello plugin loaded")

    async def on_enable(self):
        logger.info("Hello plugin enabled")

    async def on_disable(self):
        logger.info("Hello plugin disabled")

    async def execute(self, name="World"):
        return {"message": f"Hello, {name}!"}
```

**Usage:**
```python
manager = get_plugin_manager()
await manager.load_plugin("hello")
await manager.enable_plugin("hello")

plugin = manager.get_plugin("hello")
result = await plugin.execute(name="Alice")
# {"message": "Hello, Alice!"}
```

### Example 2: Custom API Plugin

See `backend/app/plugins/examples/custom_api_plugin.py` for a complete calculator API plugin example.

### Example 3: Custom Agent Plugin

See `backend/app/plugins/examples/custom_agent_plugin.py` for a complete data analyst agent plugin example.

### Example 4: Event Listener Plugin

```python
class AlertPlugin(EventListenerPlugin):
    def get_metadata(self):
        return PluginMetadata(
            id="alert_plugin",
            name="Alert Plugin",
            version="1.0.0",
            description="Sends alerts on events",
            plugin_type=PluginType.EVENT_LISTENER,
        )

    def get_event_subscriptions(self):
        return ["mission_failed", "agent_error"]

    async def on_event(self, event_type, event_data):
        if event_type == "mission_failed":
            await self.send_alert(f"Mission failed: {event_data['mission_id']}")
        elif event_type == "agent_error":
            await self.send_alert(f"Agent error: {event_data['error']}")

    async def send_alert(self, message):
        # Send to Slack, email, etc.
        logger.warning(f"ALERT: {message}")
```

---

## Best Practices

### 1. Plugin Design

**Single Responsibility**
- Each plugin should have one clear purpose
- Don't create monolithic plugins

**Minimal Dependencies**
- Keep dependencies light
- List all dependencies in metadata
- Gracefully handle missing dependencies

**Configuration**
- Use config schema for validation
- Provide sensible defaults
- Document all config options

### 2. Error Handling

**Validate Early**
```python
async def on_load(self):
    # Validate in on_load, not on_enable
    if not self.get_config("api_key"):
        raise ValueError("api_key required")
```

**Graceful Degradation**
```python
async def execute(self):
    try:
        return await self.risky_operation()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return {"error": str(e), "fallback": True}
```

**Set Error State**
```python
try:
    await self.initialize()
except Exception as e:
    self.set_error(str(e))
    raise
```

### 3. Resource Management

**Clean Up Properly**
```python
async def on_disable(self):
    # Cancel tasks
    if hasattr(self, 'task'):
        self.task.cancel()

    # Close connections
    if hasattr(self, 'connection'):
        await self.connection.close()

    # Clear caches
    self.cache.clear()
```

**Use Context Managers**
```python
async def execute(self):
    async with self.get_connection() as conn:
        result = await conn.query()
    return result
```

### 4. Testing

**Test Lifecycle**
```python
async def test_plugin_lifecycle():
    plugin = MyPlugin({})

    # Test load
    await plugin.on_load()
    assert plugin.get_status() == PluginStatus.LOADED

    # Test enable
    await plugin.on_enable()
    assert plugin.get_status() == PluginStatus.ENABLED

    # Test disable
    await plugin.on_disable()
    assert plugin.get_status() == PluginStatus.DISABLED
```

**Test Functionality**
```python
async def test_plugin_execute():
    plugin = MyPlugin({"api_key": "test"})
    await plugin.on_load()
    await plugin.on_enable()

    result = await plugin.execute(param="value")
    assert result["success"] is True
```

### 5. Security

**Validate Input**
```python
async def execute(self, user_input):
    # Sanitize input
    safe_input = sanitize(user_input)

    # Validate
    if not is_valid(safe_input):
        raise ValueError("Invalid input")
```

**Limit Permissions**
- Only request necessary permissions
- Don't store sensitive data in config
- Use secure connections

**Sandbox if Possible**
- Isolate risky operations
- Limit filesystem access
- Use timeouts

### 6. Performance

**Lazy Loading**
```python
async def on_load(self):
    # Don't initialize heavy resources here
    pass

async def on_enable(self):
    # Initialize when actually needed
    self.model = await load_ml_model()
```

**Async Operations**
```python
async def execute(self):
    # Use async for I/O
    results = await asyncio.gather(
        self.fetch_data(),
        self.process_data(),
        self.store_data()
    )
    return results
```

---

## Troubleshooting

### Plugin Not Found

**Symptom:** Plugin not listed after placing file in plugin directory

**Solutions:**
1. Check plugin file is in correct directory
2. Verify plugin class inherits from BasePlugin
3. Ensure file doesn't start with `_`
4. Check for syntax errors in plugin file
5. Restart plugin manager: `await manager.initialize()`

### Plugin Load Fails

**Symptom:** Plugin fails during load

**Solutions:**
1. Check `on_load()` implementation
2. Verify all dependencies are installed
3. Validate configuration schema
4. Check logs for specific error
5. Use `plugin.get_error()` to see error message

### Plugin Enable Fails

**Symptom:** Plugin loads but fails to enable

**Solutions:**
1. Check `on_enable()` implementation
2. Verify required resources are available
3. Check for port conflicts (API plugins)
4. Review configuration values
5. Test dependencies are accessible

### Hook Not Executing

**Symptom:** Hook callbacks not being called

**Solutions:**
1. Verify plugin is enabled (not just loaded)
2. Check event name matches exactly
3. Ensure callback is properly registered
4. Check hook execution: `await manager.execute_hook("event_name")`

### Memory Leaks

**Symptom:** Memory usage grows over time

**Solutions:**
1. Implement proper cleanup in `on_disable()`
2. Cancel all background tasks
3. Close all connections
4. Clear caches and references
5. Use weak references where appropriate

### Performance Issues

**Symptom:** Plugins slowing down system

**Solutions:**
1. Profile plugin execution
2. Use async for I/O operations
3. Implement caching
4. Reduce hook callback complexity
5. Consider disabling unused plugins

---

## Advanced Topics

### Hot Reload

```python
from backend.app.plugins import get_plugin_manager, PluginLoader

manager = get_plugin_manager()
loader = PluginLoader()

# Disable plugin
await manager.disable_plugin("my_plugin")

# Get plugin class
plugin = manager.get_plugin("my_plugin")
plugin_class = plugin.__class__

# Reload plugin code
reloaded_class = loader.reload_plugin(plugin_class)

# Update registry with new class
new_plugin = reloaded_class(plugin.config)
manager.registry.plugins["my_plugin"] = new_plugin

# Enable updated plugin
await manager.enable_plugin("my_plugin")
```

### Plugin Dependencies

```python
class DependentPlugin(GenericPlugin):
    def get_metadata(self):
        return PluginMetadata(
            id="dependent",
            dependencies=["other_plugin"],  # Requires other_plugin
            ...
        )

    async def on_load(self):
        # Check dependency is loaded
        manager = get_plugin_manager()
        if not manager.get_plugin("other_plugin"):
            raise ValueError("Dependency not loaded: other_plugin")
```

### Inter-Plugin Communication

```python
# Plugin A creates a hook
manager.hooks["plugin_a_event"] = PluginHook("plugin_a_event")

# Plugin B subscribes
class PluginB(EventListenerPlugin):
    def get_event_subscriptions(self):
        return ["plugin_a_event"]

    async def on_event(self, event_type, event_data):
        # React to Plugin A's events
        pass
```

---

## Related Documentation

- [WebSocket System](WEBSOCKET.md) - Real-time communication
- [Developer Tools](DEVELOPER_TOOLS.md) - Development utilities
- [CLAUDE.md](../CLAUDE.md) - Comprehensive development guide

---

**Created:** 2025-12-20
**Last Updated:** 2025-12-20
**Version:** 1.0.0
**Phase:** 5 - Developer Experience & Advanced Features
