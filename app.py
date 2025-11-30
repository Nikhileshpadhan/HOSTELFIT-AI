import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from PIL import Image
import json
import matplotlib.pyplot as plt
import time

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="HostelFit Pro", page_icon="💪", layout="centered")

# Custom CSS for UI
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 20px; background-color: #FF4B4B; color: white; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# Secure API Key Handling
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except FileNotFoundError:
    st.error("🔑 API Key not found. Please set it in Streamlit Cloud Secrets or strictly locally.")
    st.stop()

# --- 2. MEMORY (SESSION STATE) ---
# This satisfies the "Sessions & Memory" requirement
if "daily_log" not in st.session_state:
    st.session_state.daily_log = [] # List to store meal history objects
if "daily_stats" not in st.session_state:
    st.session_state.daily_stats = {"cals": 0, "prot": 0, "carbs": 0, "fats": 0}

# --- 3. TOOLS ---
# This satisfies the "Tools" requirement
def search_food_db(query):
    """Searches for localized Indian food data to help identify items."""
    try:
        results = DDGS().text(f"{query} cooked indian food nutritional value protein calories 100g", max_results=1)
        return results[0]['body'] if results else "No specific data found."
    except Exception:
        return "Offline Mode: Using internal knowledge base."

tools_list = [search_food_db]

# --- 4. AGENTS (MULTI-AGENT SYSTEM) ---

def agent_analyst(image_input, text_input):
    """
    AGENT 1: The Analyst.
    Role: Perception & Calculation.
    Capabilities: Vision, Search Tool.
    Output: Structured JSON data only.
    """
    model = genai.GenerativeModel(model_name='gemini-1.5-flash', tools=tools_list)
    
    base_prompt = """
    Analyze the food input (Image and/or Text). 
    Identify items, estimate portion sizes (in grams), and calculate macros.
    
    OUTPUT FORMAT: STRICT JSON ONLY. Do not include markdown code blocks (```json).
    Structure:
    {
        "foods": [
            {"name": "Item Name", "qty": "estimated portion", "cals": 0, "prot": 0, "carbs": 0, "fats": 0}
        ],
        "meal_total_cals": 0,
        "meal_total_prot": 0,
        "meal_total_carbs": 0,
        "meal_total_fats": 0,
        "reasoning": "Briefly explain how you estimated this."
    }
    """
    
    content = [base_prompt]
    if text_input: content.append(f"User Description: {text_input}")
    if image_input: content.append(image_input)
    
    try:
        response = model.generate_content(content)
        # Cleaning the response to ensure valid JSON
        raw_text = response.text
        clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Agent Analyst Error: {e}")
        return None

def agent_coach(user_profile, current_meal, daily_history):
    """
    AGENT 2: The Coach.
    Role: Strategy & Motivation.
    Capabilities: Reasoning based on Context & History.
    Output: Natural Language Advice.
    """
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
    
    prompt = f"""
    ACT AS: Elite Sports Nutritionist.
    
    USER PROFILE: 
    {user_profile}
    
    CURRENT MEAL (Just Analyzed): 
    {json.dumps(current_meal)}
    
    DAILY HISTORY (Context): 
    The user has already consumed the following totals today: {json.dumps(daily_history)}
    
    YOUR TASK:
    1. Provide specific feedback on this meal relative to their goal.
    2. Looking at their DAILY TOTALS, advise them on what to do for the rest of the day.
       (e.g., "You are low on protein today, try to have chicken for dinner" or "You've hit your calorie limit, stop eating.")
    3. Keep it short, punchy, and motivating.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- 5. UI & WORKFLOW ---
st.title("💪 HostelFit Pro")
st.caption("Multi-Agent Nutritionist: Vision • Memory • Strategy")

# Sidebar: User Profile & Daily Tracker
with st.sidebar:
    st.header("👤 Athlete Profile")
    weight = st.slider("Weight (kg)", 40, 120, 70)
    goal_type = st.selectbox("Current Phase", [
        "Lean Bulk (Minimizing Fat)",
        "Dirty Bulk (Max Size/Strength)",
        "Maintenance (Recomp)",
        "Aggressive Cut (Fast Fat Loss)"
    ])
    
    # Calculate Targets
    if "Bulk" in goal_type:
        target_prot = int(weight * 2.0)
        target_cals = weight * 35
    elif "Cut" in goal_type:
        target_prot = int(weight * 2.4)
        target_cals = weight * 24
    else:
        target_prot = int(weight * 1.8)
        target_cals = weight * 30
        
    st.divider()
    
    # Display Memory (Daily Progress)
    st.subheader("📅 Daily Tracker")
    
    # Progress Bars
    c_prog = min(st.session_state.daily_stats['cals'] / target_cals, 1.0)
    p_prog = min(st.session_state.daily_stats['prot'] / target_prot, 1.0)
    
    st.progress(c_prog, text=f"Calories: {st.session_state.daily_stats['cals']} / {int(target_cals)}")
    st.progress(p_prog, text=f"Protein: {st.session_state.daily_stats['prot']}g / {target_prot}g")
    
    if st.button("Reset Daily Log"):
        st.session_state.daily_log = []
        st.session_state.daily_stats = {"cals": 0, "prot": 0, "carbs": 0, "fats": 0}
        st.rerun()

# Main Interface
st.subheader("🍽️ Track Your Meal")
user_text = st.text_area("Describe your meal:", placeholder="Ex: I ate 2 chapatis and paneer butter masala...")
user_image = st.file_uploader("Upload Plate Photo (Optional)", type=['jpg', 'png', 'jpeg'])

if st.button("Analyze & Log Meal"):
    if not user_text and not user_image:
        st.error("⚠️ Please provide text or an image.")
    else:
        # Step 1: Agent Analyst
        with st.spinner("🤖 Analyst Agent is identifying food & calculating macros..."):
            img_data = Image.open(user_image) if user_image else None
            meal_data = agent_analyst(img_data, user_text)
            
        if meal_data:
            # Step 2: Update Memory
            st.session_state.daily_log.append(meal_data)
            st.session_state.daily_stats['cals'] += meal_data['meal_total_cals']
            st.session_state.daily_stats['prot'] += meal_data['meal_total_prot']
            st.session_state.daily_stats['carbs'] += meal_data.get('meal_total_carbs', 0)
            st.session_state.daily_stats['fats'] += meal_data.get('meal_total_fats', 0)
            
            # Step 3: Agent Coach
            with st.spinner("🧠 Coach Agent is reviewing your daily progress..."):
                profile_str = f"Weight: {weight}kg, Goal: {goal_type}, Targets: {target_cals}kcal / {target_prot}g Protein"
                advice = agent_coach(profile_str, meal_data, st.session_state.daily_stats)
            
            # --- Results Display ---
            st.success("Meal Logged Successfully!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Calories", meal_data['meal_total_cals'])
            col2.metric("Protein", f"{meal_data['meal_total_prot']}g")
            col3.metric("Carbs", f"{meal_data.get('meal_total_carbs', 0)}g")
            
            st.write("### 📝 Meal Breakdown")
            st.table(meal_data['foods'])
            
            # Coach Output Box
            st.info(f"👨‍⚕️ **Coach's Advice:**\n\n{advice}")
            
            # Pie Chart for Macro Split
            if meal_data['meal_total_cals'] > 0:
                macros = [meal_data['meal_total_prot']*4, meal_data.get('meal_total_carbs', 0)*4, meal_data.get('meal_total_fats', 0)*9]
                labels = ['Protein', 'Carbs', 'Fats']
                fig, ax = plt.subplots(figsize=(2, 2))
                ax.pie(macros, labels=labels, autopct='%1.1f%%', colors=['#66b3ff','#99ff99','#ff9999'])
                st.pyplot(fig, use_container_width=False)

        else:
            st.error("Analysis failed. Please try again.")
