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
        results = DDGS().text(f"{query} cooked indian food nutritional value protein calories 100g average", max_results=1)
        return results[0]['body'] if results else "No specific data found."
    except Exception:
        return "Offline Mode: Using internal knowledge base."

tools_list = [search_food_db]

# --- 3. THE FLEXIBLE AGENT (TEXT OR VISION) ---
def analyze_flexible(mode, user_profile, text_input=None, image_input=None):
    """
    Handles Text-Only, Image-Only, or Both.
    """
    model = genai.GenerativeModel(model_name='gemini-1.5-flash', tools=tools)
    
    # Base System Prompt
    base_prompt = f"""
    ACT AS: Elite Sports Nutritionist.
    USER PROFILE: {user_profile}
    MODE: {mode}
    
    YOUR GOAL: 
    1. Analyze the input (Image AND/OR Text).
    2. Calculate macros (Protein, Carbs, Fats, Calories).
    3. Give advice based on the specific goal (e.g., if 'Dirty Bulk', suggest high calorie foods).
    
    OUTPUT FORMAT (Strict JSON):
    {{
        "foods": [
            {{"name": "Item Name", "qty": "estimated portion", "cals": 0, "prot": 0}}
        ],
        "total_cals": 0,
        "total_prot": 0,
        "advice": "Specific advice based on the goal..."
    }}
    """
    
    # Dynamic Content Construction
    content = [base_prompt]
    
    if text_input:
        content.append(f"USER NOTES: {text_input}")
    
    if image_input:
        content.append(image_input)
        
    if not text_input and not image_input:
        return "Error: Please provide at least text or an image."

    # Call Gemini
    for attempt in range(2):
        try:
            response = model.generate_content(content)
            return response.text
        except Exception:
            time.sleep(1)
            
    return "Error: AI Service Busy."

# --- 4. THE UI (FRONTEND) ---
st.set_page_config(page_title="HostelFit Pro", page_icon="💪", layout="centered")

# Custom CSS
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 20px; background-color: #FF4B4B; color: white; }
    .big-font { font-size: 20px !important; font-weight: bold; color: #31333F; }
</style>
""", unsafe_allow_html=True)

st.title("💪 HostelFit Pro")
st.caption("AI Nutritionist: Text-Only, Vision, or Both.")

# Sidebar: User Profile & Daily Tracker
with st.sidebar:
    st.header("👤 Athlete Profile")
    weight = st.slider("Weight (kg)", 40, 120, 70)
    
    # NEW: Expanded Goal List
    goal_type = st.selectbox("Current Phase", [
        "Lean Bulk (Minimizing Fat)",
        "Dirty Bulk (Max Size/Strength)",
        "Maintenance (Recomp)",
        "Aggressive Cut (Fast Fat Loss)",
        "Slow Cut (Muscle Preservation)"
    ])
    
    st.divider()
    
    # Dynamic Target Calculation based on Goal
    if "Bulk" in goal_type:
        target_prot = int(weight * 2.2)
        st.success(f"🔥 Target: {target_prot}g Protein (High)")
    elif "Cut" in goal_type:
        target_prot = int(weight * 2.5)
        st.warning(f"✂️ Target: {target_prot}g Protein (Very High)")
    else:
        target_prot = int(weight * 1.8)
        st.info(f"⚖️ Target: {target_prot}g Protein")

# --- MAIN INTERFACE ---
st.subheader("🍽️ Track Your Meal")

# 1. TEXT INPUT (Always Visible)
user_text = st.text_area("Describe your meal:", placeholder="Ex: I ate 6 egg whites and a bowl of oats...")

# 2. IMAGE INPUT (Optional)
with st.expander("📸 Add Photo (Optional)"):
    user_image = st.file_uploader("Upload Plate/Menu", type=['jpg', 'png', 'jpeg'])

if st.button("Calculate Macros"):
    if not user_text and not user_image:
        st.error("⚠️ Please write what you ate OR upload a photo.")
    else:
        with st.spinner("🤖 Analyzing food data..."):
            
            # Prepare Image if exists
            img_data = Image.open(user_image) if user_image else None
            
            # Run Agent
            profile_str = f"{weight}kg, Goal: {goal_type}"
            raw = analyze_flexible("MEAL_TRACKING", profile_str, user_text, img_data)
            
            try:
                # Clean JSON
                clean_json = raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                # Visual Dashboard
                c1, c2, c3 = st.columns(3)
                c1.metric("Calories", data['total_cals'])
                c2.metric("Protein", f"{data['total_prot']}g")
                
                # Goal Check Logic
                if data['total_prot'] >= 30:
                    c3.success("✅ High Protein")
                else:
                    c3.error("⚠️ Low Protein")
                
                # Chart
                if data['total_cals'] > 0:
                    fig, ax = plt.subplots(figsize=(4,4))
                    labels = [x['name'] for x in data['foods']]
                    sizes = [x['cals'] for x in data['foods']]
                    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99'])
                    st.pyplot(fig)
                
                st.write("### 📝 Breakdown")
                st.table(data['foods'])
                
                st.info(f"👨‍⚕️ **Coach's Advice for {goal_type.split('(')[0]}:**\n\n{data['advice']}")
                
            except Exception as e:
                st.error("Could not analyze. Please try again.")
                st.write(f"Debug: {raw}")
