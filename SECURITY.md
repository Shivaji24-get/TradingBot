# Security Guide – TradingBot

## ⚠️  Immediate Action Required

Real API credentials and an encryption key were committed to this repository's
Git history. **You must rotate all of the following before using the bot again:**

### 1. Fyers API credentials

1. Log in to [Fyers API Dashboard](https://myapi.fyers.in/)
2. Find the app `ID52MLOEQQ-100` (or whichever matches your committed ID)
3. **Regenerate the Secret Key** (or delete the app and create a new one)
4. Update your local `config/trading_profile.yml` with the new credentials
5. **Never** commit `config/trading_profile.yml` (it is now in `.gitignore`)

### 2. Fernet encryption key (`token.key` / `token.enc`)

The encryption key and the encrypted token were both in the repository, making
the token effectively plaintext.

```bash
# Delete both files locally
rm token.key token.enc

# Re-authenticate to generate a new key pair
python -m cli.main login
```

### 3. Clean Git history (recommended)

The secrets are still visible in the repository's commit history.
Use [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) or
`git filter-repo` to remove them:

```bash
# Using BFG (easier)
bfg --delete-files token.key --delete-files token.enc
bfg --replace-text passwords.txt    # list the leaked strings

# Then force-push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

---

## Secure Credential Setup

### Environment variables (recommended)

Never store real credentials in files. Export them in your shell:

```bash
# Linux / macOS (~/.bashrc or ~/.zshrc)
export FYERS_CLIENT_ID="your_real_client_id"
export FYERS_SECRET_KEY="your_real_secret_key"

# Windows (PowerShell profile or System Properties)
$env:FYERS_CLIENT_ID = "your_real_client_id"
$env:FYERS_SECRET_KEY = "your_real_secret_key"
```

The config loader reads env vars **first**, before reading the YAML file:

```python
# utils/config.py
client_id = os.environ.get("FYERS_CLIENT_ID") or yaml_value
secret_key = os.environ.get("FYERS_SECRET_KEY") or yaml_value
```

### config/trading_profile.yml (local only)

If you prefer to store credentials in the YAML file, keep the file local and
verify it is gitignored:

```bash
# Verify it's ignored
git check-ignore -v config/trading_profile.yml
# Expected output: .gitignore:... config/trading_profile.yml
```

---

## What Is and Is NOT Committed

| File | Committed? | Contains |
|------|-----------|---------|
| `config/trading_profile.example.yml` | ✅ YES | `${ENV_VAR}` placeholders only |
| `config/trading_profile.yml` | ❌ NO (.gitignored) | Your real settings |
| `token.key` | ❌ NO (.gitignored) | Fernet encryption key |
| `token.enc` | ❌ NO (.gitignored) | Encrypted Fyers token |
| `.env` | ❌ NO (.gitignored) | Any env file |

---

## Runtime Security

| Control | Implementation |
|---------|---------------|
| Token encrypted at rest | `cryptography.Fernet` (AES-128-CBC + HMAC) |
| Token key stored separately from token | `token.key` + `token.enc` (both gitignored) |
| API calls over HTTPS | Fyers API v3 enforces TLS |
| Order confirmation required by default | `require_confirmation: true` in PipelineConfig |
| Paper trading default | `paper_trading: true` – no real orders without explicit opt-in |
| Daily loss limit | Configurable `max_daily_loss` in risk profile |

---

## Reporting a Security Issue

Please do **not** open a public GitHub issue for security vulnerabilities.
Contact the repository owner directly via email.
