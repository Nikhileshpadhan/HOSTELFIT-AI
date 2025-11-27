import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from PIL import Image
import json
import matplotlib.pyplot as plt
import time

# --- 1. SETUP & SECURITY ---
# In "Real World" apps, we NEVER hardcode keys. We use Secrets.
# On Streamlit Cloud, these are set in the dashboard. Locally, they are in .streamlit/secrets.toml
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    # Fallback for local testing if secrets.toml isn't set up
    api_key = "YOUR_API_KEY_HERE" 

genai.configure(api_key=api_key)

# --- 2. TOOLS (BACKEND) ---
def search_food_db(query):
    """Real-world tool: Searches for localized Indian food data."""
    try:
        results = DDGS().text(f"{query} nutritional value protein calories 100g indian", max_results=1)
        return results[0]['body'] if results else "No specific data found."
    except Exception as e:
        return "Offline Mode: Using internal knowledge base."

tools = [search_food_db]

# --- 3. THE VISION CORE ---
def analyze_image_with_agent(image, mode, user_profile):
    model = genai.GenerativeModel(model_name='gemini-1.5-flash-002', tools=tools)
    
    if mode == "MENU":
        prompt = f"""
        ACT AS: Expert Sports Nutritionist.
        USER PROFILE: {user_profile}
        
        TASK:
        1. Read the handwritten/printed Hostel Menu in this image.
        2. Identify items.
        3. Recommend the BEST combination for high protein.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "detected_menu": ["Item 1", "Item 2"],
            "best_combo": "Eat 2 bowls of Dal, skip the Aloo.",
            "protein_estimate": 22,
            "reasoning": "Dal has better amino acid profile than..."
        }}
        """
    else: # PLATE Analysis
        prompt = f"""
        ACT AS: AI Dietitian.
        USER PROFILE: {user_profile}
        
        TASK:
        1. Analyze this food plate.
        2. Estimate grammage/portions visually.
        3. Calculate macros.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "foods": [
                {{"name": "Rice", "qty": "200g", "cals": 260, "prot": 5}},
                {{"name": "Chicken Curry", "qty": "150g", "cals": 240, "prot": 25}}
            ],
            "total_cals": 500,
            "total_prot": 30,
            "feedback": "Great post-workout meal!"
        }}
        """
    
    # Retry logic for production reliability
    for attempt in range(2):
        try:
            response = model.generate_content([prompt, image])
            return response.text
        except Exception:
            time.sleep(1)
            
    return "Error: AI Service Busy. Please try again."

# --- 4. THE UI (FRONTEND) ---
st.set_page_config(page_title="HostelFit Pro", page_icon="🥗", layout="centered")

# Custom CSS to make it look like a Mobile App
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 20px; background-color: #FF4B4B; color: white; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🥗 HostelFit Pro")
st.caption("The AI Nutritionist for Students | Vision Powered")

# Sidebar
with st.sidebar:
    st.header("👤 Athlete Profile")
    weight = st.slider("Weight (kg)", 40, 100, 70)
    goal = st.selectbox("Goal", ["Muscle Gain", "Fat Loss", "Maintenance"])
    
    st.success(f"daily Target: {int(weight * 2)}g Protein")
    st.info("ℹ️ Privacy: Images are processed in memory and not saved.")

# Main Tabs
tab1, tab2 = st.tabs(["📸 Scan Mess Menu", "🍽️ Track My Plate"])

with tab1:
    st.write("### 📝 Today's Options")
    st.info("Snap a photo of the hostel notice board. We'll pick the best meal.")
    menu_img = st.file_uploader("Upload Menu", type=['jpg', 'png', 'jpeg'], key="menu")
    
    if menu_img:
        st.image(menu_img, caption="Menu Preview", width=300)
        if st.button("Analyze Options"):
            with st.spinner("🔍 Reading handwriting & Calculating macros..."):
                raw = analyze_image_with_agent(Image.open(menu_img), "MENU", f"{weight}kg, {goal}")
                try:
                    # Robust JSON Parsing
                    clean_json = raw.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    st.subheader("🏆 Winning Combo")
                    st.success(data['best_combo'])
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Est. Protein", f"{data['protein_estimate']}g")
                    col2.write(f"**Why?** {data['reasoning']}")
                    
                    with st.expander("See Full Menu Detected"):
                        st.write(data['detected_menu'])
                        
                except:
                    st.error("Could not read menu text clearly. Try a clearer photo.")

with tab2:
    st.write("### 🥗 Meal Tracker")
    st.info("Upload a photo of your plate. We'll count the calories.")
    plate_img = st.file_uploader("Upload Plate", type=['jpg', 'png', 'jpeg'], key="plate")
    
    if plate_img:
        st.image(plate_img, caption="Meal Preview", width=300)
        if st.button("Calculate Macros"):
            with st.spinner("🤖 Vision Agent scanning food volume..."):
                raw = analyze_image_with_agent(Image.open(plate_img), "PLATE", f"{weight}kg, {goal}")
                try:
                    clean_json = raw.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    # Dashboard Layout
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Calories", data['total_cals'])
                    c2.metric("Protein", f"{data['total_prot']}g")
                    c3.metric("Goal Status", "✅ On Track" if data['total_prot'] > 20 else "⚠️ Low")
                    
                    # Chart
                    fig, ax = plt.subplots(figsize=(4,4))
                    labels = [x['name'] for x in data['foods']]
                    sizes = [x['cals'] for x in data['foods']]
                    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99'])
                    ax.patch.set_alpha(0) # Transparent background
                    st.pyplot(fig)
                    
                    st.write("**Detailed Breakdown:**")
                    st.table(data['foods'])
                    
                except:
                    st.error("Oops! The AI got confused. Ensure food is clearly visible.")