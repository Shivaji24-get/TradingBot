# 🚀 GitHub Setup Guide

Follow these steps to push your trading bot to GitHub with a demo GIF.

## 📋 Prerequisites

1. **GitHub Account**: Create one at https://github.com if you don't have it
2. **Git**: Install from https://git-scm.com/downloads
3. **FFmpeg**: Required for GIF creation
   ```bash
   # Windows (using chocolatey)
   choco install ffmpeg
   
   # Or download from https://ffmpeg.org/download.html
   ```

## 🎬 Step 1: Create Demo GIF

### Install Required Package
```bash
pip install moviepy
```

### Edit the Script
Open `create_demo_gif.py` and adjust these parameters:
```python
create_demo_gif(
    input_video=r"C:\Users\anuma\Videos\2-Click Screen Recorder-20260418-141505.177.mp4",  # Your video path
    start_time=0,      # Skip first X seconds
    duration=15,       # GIF length in seconds (keep under 20s)
    fps=8,             # Lower = smaller file
    width=720            # Width in pixels (720 is good for GitHub)
)
```

### Run the Script
```bash
python create_demo_gif.py
```

### Optimization Tips
If your GIF is over 10MB:
1. **Reduce duration**: Change `duration=15` to `duration=10`
2. **Lower FPS**: Change `fps=8` to `fps=6` or `fps=5`
3. **Smaller width**: Change `width=800` to `width=640`
4. **Trim more**: Increase `start_time` to skip boring parts

## 🗂️ Step 2: Prepare Files

### Files to Include
✅ **Include these files:**
- `README.md` - Project documentation
- `LICENSE` - MIT license
- `requirements.txt` - Python dependencies
- `.gitignore` - Ignore sensitive files
- `demo.gif` - Demo animation
- `cli/` - CLI module
- `api/` - API module
- `auth/` - Authentication module
- `strategies/` - Trading strategies
- `utils/` - Utility functions

❌ **Never include these files:**
- `config.ini` - Contains your API credentials!
- `tokens.json` - Authentication tokens
- `__pycache__/` - Python cache
- `*.log` - Log files
- `*.csv` - Trade data
- `fyers-env/` - Virtual environment

### Update README
Edit `README.md` and update these sections:
```markdown
1. Line 5: Change `yourusername` to your actual GitHub username
2. Line 34: Update demo.gif path if needed
3. Line 231: Update GitHub issues URL
4. LICENSE file: Replace [Your Name] with your name
```

## 🌐 Step 3: Create GitHub Repository

### Option A: Using GitHub Website
1. Go to https://github.com/new
2. Repository name: `fyers-trading-bot`
3. Description: `CLI-based algorithmic trading bot for Indian stock market using Fyers API`
4. Make it **Public** (for README GIF to display properly)
5. Check **Add a README file** (we'll replace it)
6. Click **Create repository**

### Option B: Using GitHub CLI (if installed)
```bash
gh repo create fyers-trading-bot --public --description="CLI-based algorithmic trading bot for Indian stock market"
```

## 📤 Step 4: Push Code to GitHub

### Initialize Git Repository
```bash
# Navigate to your project folder
cd E:\Practice\Apr\18-04-26\TradingBot

# Initialize git
git init

# Add all files (except those in .gitignore)
git add .

# Commit
git commit -m "Initial commit: Trading bot with multi-stock scanning and live trading"
```

### Connect to GitHub
```bash
# Add remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/fyers-trading-bot.git

# Push code
git branch -M main
git push -u origin main
```

### Alternative: If GitHub repo already has files
```bash
# Pull first to avoid conflicts
git pull origin main --rebase

# Then push
git push origin main
```

## ✅ Step 5: Verify on GitHub

1. Visit `https://github.com/YOUR_USERNAME/fyers-trading-bot`
2. Check that:
   - ✅ README.md displays correctly
   - ✅ Demo GIF animates
   - ✅ All source files are present
   - ✅ No sensitive files (config.ini, tokens)

## 🎨 Step 6: Add Badges (Optional)

Edit README.md and add these badges at the top:
```markdown
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

## 🔄 Step 7: Future Updates

When you make changes:
```bash
# Add changes
git add .

# Commit with descriptive message
git commit -m "Add feature: auto-trading with risk management"

# Push to GitHub
git push origin main
```

## 🆘 Troubleshooting

### Issue: "remote: Permission denied"
**Solution**: You need to authenticate. Use:
```bash
git remote set-url origin https://USERNAME:TOKEN@github.com/USERNAME/fyers-trading-bot.git
```
Or use GitHub CLI: `gh auth login`

### Issue: GIF not displaying
**Solution**: 
1. Check file size is under 10MB
2. Ensure file is committed: `git add demo.gif`
3. Use relative path in README: `![Demo](demo.gif)`

### Issue: "Large file" warning
**Solution**: If demo.gif is too large:
```bash
# Remove from history (if accidentally committed)
git rm --cached demo.gif
git commit -m "Remove large GIF"

# Optimize and re-add
python create_demo_gif.py  # with smaller settings
git add demo.gif
git commit -m "Add optimized demo GIF"
git push
```

## 📚 Additional Resources

- [GitHub Markdown Guide](https://guides.github.com/features/mastering-markdown/)
- [GitHub GIF Optimization](https://gist.github.com/cuonggt/6649c54cc40307b1cb19300617a87e7c)
- [MoviePy Documentation](https://zulko.github.io/moviepy/)

## 🎯 Next Steps

1. ⭐ Star your own repo!
2. 📢 Share on social media
3. 🐛 Create issues for bugs
4. 🤝 Accept contributions

---

**Your trading bot is now on GitHub! 🎉**
