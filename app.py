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
    st.error("🔑 API Key not found. Please set it in Streamlit Cloud Secrets.")
    st.stop()

# --- 2. ROBUST MODEL LOADER (Fixes 404 Error) ---
def get_working_model(tools=None):
    """
    Tries multiple model names to find one that works.
    Fixes the '404 Not Found' error by trying specific versions.
    """
    model_list = [
        "gemini-1.5-flash-001",  # Most stable specific version
        "gemini-1.5-flash",      # Generic alias
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",        # Fallback to Pro
        "gemini-pro"             # Oldest fallback
    ]
    
    for model_name in model_list:
        try:
            if tools:
                return genai.GenerativeModel(model_name=model_name, tools=tools)
            else:
                return genai.GenerativeModel(model_name=model_name)
        except Exception:
            continue # Try next model
            
    # Default if all fail (will likely error later but returns an object)
    return genai.GenerativeModel(model_name='gemini-1.5-flash')

# --- 3. MEMORY (SESSION STATE) ---
if "daily_log" not in st.session_state:
    st.session_state.daily_log = [] 
if "daily_stats" not in st.session_state:
    st.session_state.daily_stats = {"cals": 0, "prot": 0, "carbs": 0, "fats": 0}

# --- 4. TOOLS ---
def search_food_db(query):
    """Searches for localized Indian food data."""
    try:
        results = DDGS().text(f"{query} cooked indian food nutritional value protein calories 100g", max_results=1)
        return results[0]['body'] if results else "No specific data found."
    except Exception:
        return "Offline Mode: Using internal knowledge base."

tools_list = [search_food_db]

# --- 5. AGENTS (MULTI-AGENT SYSTEM) ---

def agent_analyst(image_input, text_input):
    """
    AGENT 1: The Analyst.
    Role: Perception & Calculation.
    """
    # Use the robust loader to prevent 404s
    model = get_working_model(tools=tools_list)
    
    base_prompt = """
    Analyze the food input (Image and/or Text). 
    Identify items, estimate portion sizes (in grams), and calculate macros.
    
    OUTPUT FORMAT: STRICT JSON ONLY. No markdown (```json).
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
        # Clean the response text
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        st.error(f"Agent Analyst failed. Please try again. Error: {e}")
        return None

def agent_coach(user_profile, current_meal, daily_history):
    """
    AGENT 2: The Coach.
    Role: Strategy & Motivation.
    """
    model = get_working_model() # No tools needed
    
    prompt = f"""
    ACT AS: Elite Sports Nutritionist.
    USER PROFILE: {user_profile}
    CURRENT MEAL: {json.dumps(current_meal)}
    DAILY HISTORY: {json.dumps(daily_history)}
    
    YOUR TASK:
    1. Provide specific feedback on this meal relative to their goal.
    2. Advise them on what to do for the rest of the day based on their totals.
    3. Keep it short and motivating.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "Coach is offline. Good job tracking!"

# --- 6. UI & WORKFLOW ---
st.title("💪 HostelFit Pro")
st.caption("Multi-Agent Nutritionist: Vision • Memory • Strategy")

# Sidebar
with st.sidebar:
    st.header("👤 Athlete Profile")
    weight = st.slider("Weight (kg)", 40, 120, 70)
    goal_type = st.selectbox("Current Phase", [
        "Lean Bulk (Minimizing Fat)", "Dirty Bulk (Max Size)", 
        "Maintenance", "Aggressive Cut"
    ])
    
    # Target Logic
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
    st.subheader("📅 Daily Tracker")
    
    # Progress
    c_prog = min(st.session_state.daily_stats['cals'] / target_cals, 1.0)
    p_prog = min(st.session_state.daily_stats['prot'] / target_prot, 1.0)
    
    st.progress(c_prog, text=f"Calories: {st.session_state.daily_stats['cals']} / {int(target_cals)}")
    st.progress(p_prog, text=f"Protein: {st.session_state.daily_stats['prot']}g / {target_prot}g")
    
    if st.button("Reset Daily Log"):
        st.session_state.daily_log = []
        st.session_state.daily_stats = {"cals": 0, "prot": 0, "carbs": 0, "fats": 0}
        st.rerun()

# Main Area
st.subheader("🍽️ Track Your Meal")
user_text = st.text_area("Describe your meal:", placeholder="Ex: 2 chapatis and dal...")
user_image = st.file_uploader("Upload Plate Photo (Optional)", type=['jpg', 'png', 'jpeg'])

if st.button("Analyze & Log Meal"):
    if not user_text and not user_image:
        st.error("⚠️ Please provide text or an image.")
    else:
        # Agent 1
        with st.spinner("🤖 Analyst Agent is calculating macros..."):
            img_data = Image.open(user_image) if user_image else None
            meal_data = agent_analyst(img_data, user_text)
            
        if meal_data:
            # Update Memory
            st.session_state.daily_log.append(meal_data)
            st.session_state.daily_stats['cals'] += meal_data.get('meal_total_cals', 0)
            st.session_state.daily_stats['prot'] += meal_data.get('meal_total_prot', 0)
            st.session_state.daily_stats['carbs'] += meal_data.get('meal_total_carbs', 0)
            st.session_state.daily_stats['fats'] += meal_data.get('meal_total_fats', 0)
            
            # Agent 2
            with st.spinner("🧠 Coach Agent is strategizing..."):
                profile_str = f"Weight: {weight}kg, Goal: {goal_type}"
                advice = agent_coach(profile_str, meal_data, st.session_state.daily_stats)
            
            # Display
            st.success("Meal Logged!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Calories", meal_data.get('meal_total_cals', 0))
            col2.metric("Protein", f"{meal_data.get('meal_total_prot', 0)}g")
            col3.metric("Carbs", f"{meal_data.get('meal_total_carbs', 0)}g")
            
            st.table(meal_data.get('foods', []))
            st.info(f"👨‍⚕️ **Coach's Advice:**\n\n{advice}")
            
            # Charts
            if meal_data.get('meal_total_cals', 0) > 0:
                macros = [
                    meal_data.get('meal_total_prot', 0)*4, 
                    meal_data.get('meal_total_carbs', 0)*4, 
                    meal_data.get('meal_total_fats', 0)*9
                ]
                fig, ax = plt.subplots(figsize=(2, 2))
                ax.pie(macros, labels=['Prot', 'Carb', 'Fat'], autopct='%1.1f%%', colors=['#66b3ff','#99ff99','#ff9999'])
                st.pyplot(fig, use_container_width=False)
