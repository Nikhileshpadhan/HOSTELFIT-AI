# HostelFit Pro 🚀  

HostelFit Pro is a multi-agent AI nutrition assistant built for students and athletes who want accurate diet tracking — even in hostel environments. By combining computer vision, web search, and specialized AI agents, it delivers instant macronutrient analysis and personalized coaching from meal photos or text descriptions.

---

## 🛠️ How It Works  

HostelFit Pro uses a **Multi-Agent System** that processes data in structured stages:

### 1️⃣ Analyst Agent — Perception & Calculation  
- Uses **Google Gemini 1.5 Flash** to analyze uploaded meal images or text inputs (e.g., “2 chapatis and dal”).  
- If unfamiliar food is detected, a DuckDuckGo-powered search tool retrieves localized nutritional data.  
- Returns estimated weight (grams), calories, protein, carbohydrates, and fats in strict JSON format.  

### 2️⃣ Memory & Progress Tracking  
- Maintains session-based memory of all logged meals.  
- Tracks cumulative intake against dynamically calculated targets based on:  
  - Lean Bulk  
  - Dirty Bulk  
  - Maintenance  
  - Aggressive Cut  

### 3️⃣ Coach Agent — Strategy & Optimization  
- Acts as an Elite Sports Nutritionist AI.  
- Reviews daily intake and meal history.  
- Provides actionable suggestions to align remaining meals with protein and calorie goals.  

---

## 🚀 Key Features  

- 📸 Upload meal photos for instant macro breakdown  
- 🇮🇳 Optimized for Indian foods like chapati, dal, and regional dishes  
- 🎯 Dynamic calorie and protein goal adjustment  
- 📊 Pie charts for macronutrient distribution  
- 🧠 Multi-agent architecture (Analysis + Memory + Coaching)  

---

## 📦 Installation & Setup  

### Prerequisites  
- Python 3.8+  
- Google Gemini API Key  

### 1️⃣ Clone Repository  

```bash
git clone https://github.com/nikhileshpadhan/hostelfit-ai.git
cd hostelfit-ai
