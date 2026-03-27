import streamlit as st
import os
import json
from dotenv import load_dotenv

from src.config import PipelineConfig
from src.extractor import fetch_market_dashboard
from src.ai_engine import generate_structured_script, generate_structured_script_with_prompt
from src.scene_planner import build_scene_blueprint
from src.insight_engine import compute_market_insights
from src.validation import validate_dashboard
from src.pipeline_runner import run_pipeline

load_dotenv()

st.set_page_config(page_title="AI Market Video Engine V5", page_icon="📱", layout="wide")
st.title("📱 AI Market Video Engine (V5)")
st.markdown("Automated market video generation powered by **Groq AI** (llama-3.3-70b-versatile).")

api_key = os.getenv("GROQ_API_KEY")

if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
    st.warning("⚠️ GROQ_API_KEY not set in VideoGen/.env — script generation will fail.")
else:
    st.success("✅ Groq API Key configured!")

# Initialize session state
if "pipeline_state" not in st.session_state:
    st.session_state.pipeline_state = {
        "step": "waiting",
        "dashboard": None,
        "script_json": None,
        "gemini_prompt": None,
        "error": None,
    }

def reset_pipeline():
    """Reset pipeline state to start over."""
    st.session_state.pipeline_state = {
        "step": "waiting",
        "dashboard": None,
        "script_json": None,
        "gemini_prompt": None,
        "error": None,
    }

def fetch_data():
    """Fetch market data from yfinance."""
    st.session_state.pipeline_state["step"] = "fetching"
    st.session_state.pipeline_state["dashboard"] = fetch_market_dashboard()
    st.session_state.pipeline_state["step"] = "data_ready"

def generate_script():
    """Generate script via Gemini, fallback to manual input if API fails."""
    state = st.session_state.pipeline_state
    dashboard = state.get("dashboard")
    
    if not dashboard:
        st.error("No market data available. Please fetch data first.")
        return
    
    st.session_state.pipeline_state["step"] = "generating_script"
    
    # Validate and normalize dashboard
    dashboard_normalized, skipped = validate_dashboard(dashboard)
    insight = compute_market_insights(dashboard_normalized)
    scene_blueprint = build_scene_blueprint(dashboard_normalized, insight)
    
    # Try to generate script via Gemini and capture the prompt
    prompt, script_json, status = generate_structured_script_with_prompt(dashboard_normalized, scene_blueprint, expected_scenes=7)
    
    # Store prompt for manual fallback
    st.session_state.pipeline_state["gemini_prompt"] = prompt
    
    # Check result source
    if status.get("source") == "groq" and status.get("status") == "success":
        st.session_state.pipeline_state["script_json"] = script_json
        st.session_state.pipeline_state["step"] = "script_ready"
        st.success("✅ Script generated successfully via Groq!")
    else:
        st.session_state.pipeline_state["error"] = status.get("reason", "Groq API failed or unavailable.")
        st.session_state.pipeline_state["step"] = "manual_input_required"

def process_manual_script(manual_json: str):
    """Accept and validate manually provided script JSON."""
    try:
        script_data = json.loads(manual_json)
        # Basic validation
        if "scenes" not in script_data:
            st.error("Script must contain 'scenes' field.")
            return
        st.session_state.pipeline_state["script_json"] = script_data
        st.session_state.pipeline_state["step"] = "script_ready"
        st.success("✅ Manual script accepted!")
        st.rerun()
    except json.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON format: {e}")

def generate_video():
    """Generate final video from script and market data."""
    state = st.session_state.pipeline_state
    
    if not state.get("script_json"):
        st.error("No script available. Please generate or provide script first.")
        return
    
    if not state.get("dashboard"):
        st.error("No market data available. Please fetch data first.")
        return
    
    with st.status("🎬 Generating video...", expanded=True) as status:
        cfg = PipelineConfig.from_env()
        
        st.write("1️⃣ Rendering visuals and scene assets...")
        st.write("2️⃣ Synthesizing narration audio...")
        st.write("3️⃣ Creating captions with text-to-image...")
        st.write("4️⃣ Compositing video with MoviePy...")
        
        result = run_pipeline(
            config=cfg, 
            script_override=state["script_json"], 
            dashboard_override=state.get("dashboard")
        )
        
        status.update(label="✅ Video generation complete!", state="complete", expanded=False)
    
    if result.get("ok"):
        video_path = result.get("video_path")
        metadata_path = result.get("metadata_path")
        
        st.success(f"✅ Video saved to: {video_path}")
        st.video(video_path)
        
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            st.subheader("📤 Publishing Information")
            publishing = metadata.get("publishing", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Title:** {publishing.get('title_options', ['Market Update'])[0]}")
            with col2:
                st.info(f"**Hashtags:** {', '.join(publishing.get('hashtags', []))}")
            
            with st.expander("View Full Metadata"):
                st.json(metadata)
    else:
        st.error(f"❌ Video generation failed: {result.get('error')}")

# Main UI Layout
st.header("📺 Interactive Video Generation Pipeline")

col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("Step 1: Fetch Market Data")
with col2:
    if st.button("🔄 Reset", key="reset_btn"):
        reset_pipeline()
        st.rerun()

if st.button("📊 Fetch Real-Time Market Data", use_container_width=True, type="primary"):
    with st.spinner("Fetching indices, sectors, and market metadata..."):
        fetch_data()
    st.rerun()

state = st.session_state.pipeline_state

# Dashboard summary if data is fetched
if state.get("dashboard"):
    dashboard = state["dashboard"]
    indices = dashboard.get("Indices", [])
    sectors = (dashboard.get("Sectors", {}) or {}).get("All", [])
    skipped = dashboard.get("Meta", {}).get("Skipped_Symbols", [])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📈 Indices", len(indices))
    with col2:
        st.metric("🏭 Sectors", len(sectors))
    with col3:
        st.metric("⚠️ Skipped", len(skipped))
    
    st.divider()
    
    # Step 2: Script Generation or Manual Input
    st.subheader("Step 2: Script Generation")
    
    if state["step"] == "data_ready":
        if st.button("🤖 Generate Script (Groq AI)", use_container_width=True, type="primary"):
            with st.spinner("Generating script with AI..."):
                generate_script()
            st.rerun()
    
    elif state["step"] == "generating_script":
        st.info("⏳ Generating script with Groq AI...")
    
    elif state["step"] == "manual_input_required":
        st.error(f"⚠️ {state.get('error', 'Script generation failed')}")
        
        st.divider()
        
        # Option 1: Show the prompt that was sent to Groq
        st.subheader("💡 Option 1: View Generated Prompt")
        
        if state.get("gemini_prompt"):
            with st.expander("📋 View the Groq prompt that was sent"):
                st.code(state["gemini_prompt"], language="text", line_numbers=True)
        
        st.divider()
        
        # Option 2: Provide JSON manually
        st.subheader("💡 Option 2: Paste Script JSON Here")
        
        manual_json = st.text_area(
            "Paste a script JSON (must have 'video_title' and 'scenes' array):",
            height=300,
            placeholder='{"video_title": "...", "scenes": [{...}]}',
            key="manual_response_input",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Accept Script JSON", use_container_width=True, type="primary"):
                if manual_json.strip():
                    process_manual_script(manual_json)
                else:
                    st.error("Please paste the script JSON first.")
        
        with col2:
            if st.button("🔄 Retry Groq API", use_container_width=True):
                st.session_state.pipeline_state["step"] = "data_ready"
                st.rerun()
        
        st.divider()
        
        # Option 3: Use sample script
        st.subheader("💡 Option 3: Use Sample Script (Quick Start)")
        
        if st.button("📋 Load Sample Script", use_container_width=True):
            sample = {
                "video_title": "Indian Market Daily Update",
                "scenes": [
                    {
                        "scene_number": 1,
                        "title": "Intro",
                        "voiceover": "Welcome to your daily market update!",
                        "caption": "MARKET UPDATE"
                    },
                    {
                        "scene_number": 2,
                        "title": "Indices",
                        "voiceover": "Nifty 50 and Sensex closed with mixed movements today.",
                        "caption": "INDICES UPDATE"
                    },
                    {
                        "scene_number": 3,
                        "title": "Volatility",
                        "voiceover": "India VIX remains stable, indicating calm market conditions.",
                        "caption": "VIX STABLE"
                    },
                    {
                        "scene_number": 4,
                        "title": "Winners",
                        "voiceover": "Banking and Pharma sectors led today's gains.",
                        "caption": "GAINERS STRONG"
                    },
                    {
                        "scene_number": 5,
                        "title": "Losers",
                        "voiceover": "Auto and Metal sectors saw minor declines.",
                        "caption": "SOME WEAKNESS"
                    },
                    {
                        "scene_number": 6,
                        "title": "Insight",
                        "voiceover": "Institutional buying continues to support the rally.",
                        "caption": "POSITIVE FLOWS"
                    },
                    {
                        "scene_number": 7,
                        "title": "Close",
                        "voiceover": "Stay tuned for tomorrow's update. Subscribe now!",
                        "caption": "SUBSCRIBE"
                    }
                ]
            }
            sample_json = json.dumps(sample, indent=2)
            st.code(sample_json, language="json")
            
            if st.button("✅ Use This Sample", use_container_width=True, key="use_sample_btn"):
                process_manual_script(sample_json)
    
    elif state["step"] == "script_ready":
        st.success("✅ Script ready for video generation")
        
        with st.expander("📋 View Script Preview"):
            st.json(state["script_json"])
        
        st.divider()
        
        # Step 3: Video Generation
        st.subheader("Step 3: Generate Final Video")
        
        if st.button("🎬 Generate Video", use_container_width=True, type="primary"):
            generate_video()
else:
    st.info("👆 Click **'Fetch Real-Time Market Data'** to begin the video generation pipeline.")
