# 🚀 Setup Guide: Free Groq API for ChatOps CLI

## Why Groq?
- ⚡ **Lightning Fast**: 500+ tokens/second (fastest LLM API available)
- 🆓 **Generous Free Tier**: 6,000 requests/day 
- 🤖 **Great Models**: Llama3-8B, Mixtral-8x7B, Gemma-7B
- 🔧 **Perfect for Learning**: No memory constraints, works on any machine

---

## Step 1: Get Your Free Groq API Key

1. **Visit Groq Console**: https://console.groq.com/keys
2. **Sign up** for a free account (GitHub/Google login available)
3. **Create API Key**: Click "Create API Key"
4. **Copy the key**: It looks like `gsk_xyz123...`

---

## Step 2: Configure Your Environment

Create a `.env` file in your project root:

```bash
# .env file
GROQ_API_KEY=gsk_your_actual_api_key_here
DEFAULT_LLM_PROVIDER=groq
GROQ_MODEL=llama3-8b-8192
DEBUG_MODE=true
```

---

## Step 3: Available Models

Choose the best model for your needs:

| Model | Description | Speed | Quality | Use Case |
|-------|-------------|-------|---------|----------|
| `llama3-8b-8192` | **Recommended** | Fastest | Very Good | Development, Testing |
| `llama3-70b-8192` | Most Capable | Fast | Excellent | Production, Complex Tasks |
| `mixtral-8x7b-32768` | Balanced | Fast | Great | General Purpose |
| `gemma-7b-it` | Google's Model | Fast | Good | Alternative Option |

---

## Step 4: Test Your Setup

```bash
# Test Groq integration
python -m poetry run python test_groq.py
```

---

## Step 5: Run ChatOps CLI with Groq

```bash
# Test with Groq API (no memory constraints!)
python -m poetry run python -m chatops_cli ask "check disk usage"

# Verify Groq is working
python -m poetry run python -m chatops_cli --debug ask "show system info"
```

---

## 🎯 Benefits of This Setup

### ✅ **No Memory Issues**
- No need for 8GB+ RAM
- No local model downloads
- Works on any machine

### ✅ **Lightning Fast**
- 500+ tokens/second response time
- Much faster than local LLMs
- Near-instant command generation

### ✅ **Production Ready** 
- Enterprise-grade API
- 99.9% uptime
- Scalable for real projects

### ✅ **Free & Generous**
- 6,000 requests/day free
- No credit card required
- Perfect for learning & development

---

## 🔧 Troubleshooting

### API Key Issues
```bash
# Check if API key is loaded
python -c "from chatops_cli.config import settings; print('API Key configured:', bool(settings.groq_api_key))"
```

### Connection Issues
```bash
# Test Groq connection directly
python -c "
import asyncio
from chatops_cli.core.groq_client import GroqClient

async def test():
    client = GroqClient()
    connected = await client.connect()
    print('Groq connected:', connected)

asyncio.run(test())
"
```

### Model Selection
```bash
# List available models
python -c "from chatops_cli.core.groq_client import GroqClient; print(GroqClient().list_available_models())"
```

---

## 🎉 Ready to Go!

Your ChatOps CLI now has:
- ✅ **Free LLM API** (no memory constraints)
- ✅ **Lightning-fast responses** 
- ✅ **Production-quality AI**
- ✅ **Plugin system as fallback**

**Perfect balance of speed, quality, and cost!** 🚀 