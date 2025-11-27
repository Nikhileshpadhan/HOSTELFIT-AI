import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from PIL import Image
import json
import matplotlib.pyplot as plt
import time

# --- 1. SETUP & SECURITY ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("🔑 API Key not found. Please set it in Streamlit Cloud Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. TOOLS (BACKEND) ---
def search_food_db(query):
    """Real-world tool: Searches for localized Indian food data."""
    try:
        # We add 'cooked' and 'average' to get better real-world estimates
        results = DDGS().text(f"{query} cooked indian food nutritional value protein calories 100g average", max_results=1)
        return results[0]['body'] if results else "No specific data found."
    except Exception as e:
        return "Offline Mode: Using internal knowledge base."

tools = [search_food_db]

# --- 3. THE VISION CORE ---
def analyze_multimodal(image, text_context, mode, user_profile):
    """
    Combines Image + Text Context + User Profile into one prompt.
    """
    model = genai.GenerativeModel(model_name='gemini-1.5-flash-002', tools=tools)
    
    if mode == "MENU":
        prompt = f"""
        ACT AS: Expert Sports Nutritionist for a student hostel.
        USER PROFILE: {user_profile}
        EXTRA CONTEXT FROM USER: "{text_context}"
        
        TASK:
        1. Read the menu in the image.
        2. Consider the user's extra notes (e.g., allergies, preferences).
        3. Recommend the single best high-protein combination.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "best_combo": "Eat 2 bowls of Dal, skip the Aloo.",
            "protein_estimate": 22,
            "reasoning": "Based on your note about avoiding dairy, this is the best plant-based option..."
        }}
        """
    else: # PLATE Analysis
        prompt = f"""
        ACT AS: AI Dietitian.
        USER PROFILE: {user_profile}
        EXTRA CONTEXT FROM USER: "{text_context}"
        
        TASK:
        1. Analyze the food on the plate image.
        2. Adjust portion estimates based on the user's text context (e.g., "I only ate half").
        3. Calculate final macros.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "foods": [
                {{"name": "Rice", "qty": "100g (Half portion)", "cals": 130, "prot": 2.5}},
                {{"name": "Chicken Curry", "qty": "150g", "cals": 240, "prot": 25}}
            ],
            "total_cals": 370,
            "total_prot": 27.5,
            "feedback": "Good job adjusting for your actual intake."
        }}
        """
    
    # Retry logic
    for attempt in range(2):
        try:
            response = model.generate_content([prompt, image])
            return response.text
        except Exception:
            time.sleep(1)
            
    return "Error: AI Service Busy. Please try again."

# --- 4. THE UI (FRONTEND) ---
st.set_page_config(page_title="HostelFit Pro", page_icon="🥗", layout="centered")

# Custom CSS
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 20px; background-color: #FF4B4B; color: white; }
    .big-font { font-size: 20px !important; font-weight: bold; color: #31333F; }
</style>
""", unsafe_allow_html=True)

# Starter Message
st.markdown('<p class="big-font">👋 Hi there! I\'m HostelFit Pro.</p>', unsafe_allow_html=True)
st.write("I'm here to help you hit your protein goals, even in the hostel mess. Show me a menu or your plate, give me some context, and I'll do the math.")
st.divider()

# Sidebar
with st.sidebar:
    st.header("👤 Athlete Profile")
    weight = st.slider("Weight (kg)", 40, 100, 70)
    goal = st.selectbox("Goal", ["Muscle Gain", "Fat Loss"])
    profile_str = f"{weight}kg, {goal}"
    st.success(f"Daily Target: {int(weight * 2)}g Protein")

# Main Tabs
tab1, tab2 = st.tabs(["📸 Scan Mess Menu", "🍽️ Track My Plate"])

with tab1:
    st.write("### 📝 What's on the menu?")
    # Added Text Input
    menu_text = st.text_area("Add notes (optional)", placeholder="e.g., 'I'm allergic to nuts' or 'I hate paneer'", key="menu_txt")
    menu_img = st.file_uploader("Upload Menu Photo", type=['jpg', 'png', 'jpeg'], key="menu_img")
    
    if menu_img and st.button("Analyze Options"):
        # Basic validation
        if not api_key: st.error("API Key missing."); st.stop()

        with st.spinner("🔍 Reading menu & thinking..."):
            raw = analyze_multimodal(Image.open(menu_img), menu_text, "MENU", profile_str)
            try:
                clean_json = raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                st.subheader("🏆 Winning Combo")
                st.success(data['best_combo'])
                st.metric("Est. Protein", f"{data['protein_estimate']}g")
                st.write(f"**Why?** {data['reasoning']}")
            except:
                st.error("Could not read menu clearly. Try a better photo.")

with tab2:
    st.write("### 🥗 What did you eat?")
    # Added Text Input
    plate_text = st.text_area("Add notes (optional)", placeholder="e.g., 'I left half the rice' or 'Added extra ghee'", key="plate_txt")
    plate_img = st.file_uploader("Upload Plate Photo", type=['jpg', 'png', 'jpeg'], key="plate_img")
    
    if plate_img and st.button("Calculate Macros"):
        if not api_key: st.error("API Key missing."); st.stop()

        with st.spinner("🤖 Scanning plate & adjusting for your notes..."):
            raw = analyze_multimodal(Image.open(plate_img), plate_text, "PLATE", profile_str)
            try:
                clean_json = raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                # Dashboard
                c1, c2 = st.columns(2)
                c1.metric("Calories", data['total_cals'])
                c2.metric("Protein", f"{data['total_prot']}g")
                
                # Chart
                fig, ax = plt.subplots(figsize=(4,4))
                labels = [x['name'] for x in data['foods']]
                sizes = [x['cals'] for x in data['foods']]
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99'])
                st.pyplot(fig)
                
                st.write("**Detailed Breakdown:**")
                st.table(data['foods'])
                st.info(f"💡 {data['feedback']}")
            except:
                st.error("Oops! The AI got confused. Ensure food is clearly visible.")
