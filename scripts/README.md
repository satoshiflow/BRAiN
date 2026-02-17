# BRAiN Scripts

Utility scripts for development and operations.

## Aider + Moonshot Kimi Integration

Two launcher scripts for using [Aider](https://aider.chat/) with Moonshot's Kimi API:

### Quick Start

1. **Add your Moonshot API key** to either `.env` or `backend/.env`:
   ```bash
   MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxx
   ```

   Get your key from: https://platform.moonshot.cn/console/api-keys

2. **Install Aider** (if not already installed):
   ```bash
   pip install aider-chat
   # or with pipx for isolation
   pipx install aider-chat
   ```

3. **Run Aider with Kimi**:
   ```bash
   # Standard Kimi K2 model
   ./scripts/aider-kimi.sh

   # Thinking/reasoning model (slower, better for complex tasks)
   ./scripts/aider-kimi-thinking.sh
   ```

### Scripts

#### `aider-kimi.sh`
Main launcher that:
- Loads `.env` files from root and `backend/`
- Configures OpenAI-compatible environment for Moonshot
- Runs Aider with `openai/kimi-k2` model by default
- Passes through additional Aider arguments

**Usage:**
```bash
# Basic usage
./scripts/aider-kimi.sh

# With specific files
./scripts/aider-kimi.sh backend/api/routes/*.py

# Override model
./scripts/aider-kimi.sh openai/kimi-k2-thinking

# Additional Aider flags
./scripts/aider-kimi.sh --no-auto-commits --message "Add feature X"
```

#### `aider-kimi-thinking.sh`
Convenience wrapper that uses the thinking/reasoning model variant:
```bash
./scripts/aider-kimi-thinking.sh
```

### Environment Configuration

The scripts configure these environment variables automatically:

```bash
OPENAI_API_KEY=$MOONSHOT_API_KEY
OPENAI_API_BASE=https://api.moonshot.ai/v1
OPENAI_BASE_URL=https://api.moonshot.ai/v1
```

### Model Selection

Available Moonshot models (via OpenAI-compatible endpoint):

- `openai/kimi-k2` - Standard model (default)
- `openai/kimi-k2-thinking` - Reasoning model (slower, better for complex tasks)

### Troubleshooting

**"MOONSHOT_API_KEY not found"**
- Add your API key to `.env` or `backend/.env`
- Check for typos in the variable name
- Ensure `.env` file is in the project root

**"aider not found in PATH"**
- Install Aider: `pip install aider-chat`
- Or with pipx: `pipx install aider-chat`

**LiteLLM provider errors**
- The scripts explicitly set OpenAI environment variables
- If you still get errors, check that no conflicting env vars are set
- Try: `env | grep -i openai` to see what's set

**Rate limiting**
- Moonshot has rate limits on their API
- Reduce request frequency or upgrade your plan
- Consider using the standard model instead of thinking model

### Cost Optimization

Moonshot Kimi is significantly cheaper than OpenAI/Anthropic:
- Use `kimi-k2` for standard coding tasks
- Reserve `kimi-k2-thinking` for complex architecture decisions
- Aider's caching helps reduce costs

### Other Scripts

- `dmz-fw.sh` - DMZ firewall configuration
- `sovereign-fw.sh` - Sovereign mode firewall
- `verify-sovereign-mode.sh` - Sovereign mode verification
- `network-probe.sh` - Network diagnostics
- `load_example_policies.py` - Load example policies
- `run_integration_tests.sh` - Integration test runner
