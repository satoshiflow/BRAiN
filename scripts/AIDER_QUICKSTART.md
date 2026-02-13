# Aider + Kimi Quick Start Guide

## ✅ Setup Complete!

Your Moonshot Kimi API key is configured and ready to use.

## 🚀 Usage

### Standard Model (Fast & Cost-Effective)
```bash
cd ~/dev/brain-v2
./scripts/aider-kimi.sh
```

### Thinking Model (Complex Tasks)
```bash
./scripts/aider-kimi-thinking.sh
```

### With Specific Files
```bash
./scripts/aider-kimi.sh backend/api/routes/*.py
```

### Non-Interactive Mode
```bash
./scripts/aider-kimi.sh --yes --message "Add logging to function X" file.py
```

## 📊 Model Comparison

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| `moonshot-v1-8k` | 8K tokens | ⚡ Fast | 💰 Low | Standard coding, refactoring, bug fixes |
| `moonshot-v1-32k` | 32K tokens | 🐌 Slower | 💰💰 Medium | Architecture, complex logic, large files |
| `moonshot-v1-128k` | 128K tokens | 🐌 Slowest | 💰💰💰 Higher | Whole codebase analysis |

## 🔧 Configuration

API key location: `backend/.env`
```bash
MOONSHOT_API_KEY=sk-...
```

The launcher automatically configures:
- `OPENAI_API_BASE=https://api.moonshot.ai/v1`
- `OPENAI_API_KEY=$MOONSHOT_API_KEY`

## 💡 Tips

1. **Start simple**: Begin with `./scripts/aider-kimi.sh` and no file arguments
2. **Use --yes flag**: For automated workflows, add `--yes` to skip confirmations
3. **Cost control**: Stick to `moonshot-v1-8k` for routine tasks, use 32k for larger contexts
4. **Git integration**: Aider creates commits automatically (use `--no-auto-commits` to disable)

## 🐛 Troubleshooting

### Connection Issues
```bash
# Test API key manually
curl -H "Authorization: Bearer $MOONSHOT_API_KEY" \
     https://api.moonshot.ai/v1/models
```

### Wrong Model Selected
The script uses `openai/moonshot-v1-8k` by default. To override:
```bash
# Use 32k context model
./scripts/aider-kimi.sh openai/moonshot-v1-32k

# Use 128k context model for large codebases
./scripts/aider-kimi.sh openai/moonshot-v1-128k
```

### Environment Issues
```bash
# Check if API key is loaded
grep MOONSHOT backend/.env
```

## 📚 Resources

- [Aider Documentation](https://aider.chat/docs/)
- [Moonshot Platform](https://platform.moonshot.cn/)
- [Model Pricing](https://platform.moonshot.cn/pricing)

## ⚡ Quick Examples

```bash
# Bug fix
./scripts/aider-kimi.sh --yes \
  --message "Fix the null pointer error in line 42" \
  backend/api/routes/users.py

# Refactor
./scripts/aider-kimi.sh \
  --message "Extract duplicate code into a helper function" \
  backend/utils/*.py

# Add feature
./scripts/aider-kimi.sh \
  --message "Add rate limiting to the API endpoint" \
  backend/api/routes/missions.py
```
