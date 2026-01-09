# description_generator.py
themes = ["Fireplace", "Rain", "Ocean", "Space", "Coffee Shop", "Forest", "City Night"]

def simple_description(theme_idx=0, day=1):
    theme = themes[theme_idx]
    
    return f"""🔴 LIVE: {theme} Study Music • 24/7

Perfect for studying, coding, focus, and relaxation.

Theme: {theme}
Duration: 12 Hours
Status: 🔴 Live Now

━━━━━━━━━━━━━━━━
👨‍💻 By Vallarasu K
━━━━━━━━━━━━━━━━

🔗 Portfolio: vallarasuk.com
🔗 Dev Portfolio: dev.vallarasuk.com
🔗 GitHub: github.vallarasuk.com
🔗 LinkedIn: linkedin.vallarasuk.com

🛠️ My Tools:
• VS Code Extension: Auto Console Log
• Chrome Extensions: Tech Stack Checker, Opacity Adjuster
• Web Apps: ATS Resume Maker, Place Finder, Book Library

👥 Community: squad.vallarasuk.com

⭐ Please Like, Subscribe & Share!

#StudyWithMe #FocusMusic #{theme.replace(' ', '')} #StudyStream
"""

# Generate for today
print(simple_description(day=1))