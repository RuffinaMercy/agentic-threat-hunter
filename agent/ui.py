"""
Simplified Streamlit UI for AI News Agent Security Demo.

Streamlined design: radio button for mode selection, no approval checkbox,
clean observability dashboard.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml


# ============================================================================
# Configuration
# ============================================================================

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = PROJECT_ROOT / "agent"
STATE_FILE = PROJECT_ROOT / "data" / "agent_state.json"
SKILLS_DIR = PROJECT_ROOT / "skills"
AGENT_FILE = AGENT_DIR / "agent.py"
POLICIES_FILE = AGENT_DIR / "policies.yaml"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_JSONL_FILE = LOGS_DIR / "agent_logs.jsonl"
METRICS_DB_FILE = LOGS_DIR / "metrics.db"

st.set_page_config(
    page_title="AI News Agent – Security Demo",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Utility Functions
# ============================================================================

def read_state() -> Dict[str, Any]:
    """Load agent state from JSON file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def load_jsonl_logs() -> pd.DataFrame:
    """Load JSONL logs into DataFrame."""
    if not LOGS_JSONL_FILE.exists():
        return pd.DataFrame()
    
    try:
        events = []
        with open(LOGS_JSONL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if not events:
            return pd.DataFrame()
        
        df = pd.DataFrame(events)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp", ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading logs: {e}")
        return pd.DataFrame()


def load_metrics_db() -> pd.DataFrame:
    """Load metrics from SQLite database."""
    if not METRICS_DB_FILE.exists():
        return pd.DataFrame()
    
    try:
        conn = sqlite3.connect(METRICS_DB_FILE)
        df = pd.read_sql_query(
            "SELECT * FROM run_metrics ORDER BY finished_at DESC LIMIT 50",
            conn
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading metrics: {e}")
        return pd.DataFrame()


def load_policies() -> Dict[str, Any]:
    """Load policies from YAML."""
    if POLICIES_FILE.exists():
        try:
            return yaml.safe_load(POLICIES_FILE.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, UnicodeDecodeError):
            return {}
    return {}


# ============================================================================
# Main UI Tabs
# ============================================================================

def render_run_tab():
    """Simplified Run Agent tab with radio button mode selection."""
    state = read_state()
    
    st.markdown("### 🚀 Run Agent")
    
    # Status box
    if state.get("done") and state.get("date") == date.today().isoformat():
        st.info(
            "✅ Today's run is complete. Use **Reset State** for a fresh start.",
            icon="ℹ️"
        )
    
    # Mode selection with radio button
    st.markdown("**Select Mode:**")
    mode = st.radio(
        "Select execution mode",
        options=["Secure Mode", "Attack Demo Mode"],
        index=0,
        help=(
            "**Secure Mode**: Only signed skills run (Standard Summarizer). "
            "**Attack Demo Mode**: All skills load, highest-rated malicious skill is selected."
        ),
        label_visibility="collapsed"
    )
    
    # Control buttons
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        run_clicked = st.button(
            "▶ Run Agent",
            type="primary",
            width="stretch",
            help="Execute the agent with selected mode"
        )
    
    with col2:
        reset_clicked = st.button(
            "🗑 Reset State",
            width="stretch",
            help="Clear previous run and start fresh"
        )
    
    # Handle reset
    if reset_clicked:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        st.success("✅ State reset. Next run will start fresh.")
        st.rerun()
    
    # Handle run
    if run_clicked:
        st.divider()
        
        # Build command
        cmd = [sys.executable, str(AGENT_FILE)]
        if mode == "Attack Demo Mode":
            cmd.append("--skip-verification")
        
        # Set environment to auto-approve when running from UI
        env = os.environ.copy()
        env["AGENT_APPROVE_SKILL"] = "yes"  # Auto-approve in UI mode
        env["PYTHONUNBUFFERED"] = "1"
        
        # Run agent as subprocess from project root
        with st.spinner("⏳ Agent is running..."):
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            
            # Capture output in real-time
            logs = []
            log_placeholder = st.empty()
            for line in process.stdout:
                logs.append(line.rstrip())
                log_placeholder.code("\n".join(logs[-50:]), language="text")
            
            return_code = process.wait()
            full_output = "\n".join(logs)
        
        # Show result
        if return_code == 0:
            st.success("✅ Agent run completed successfully.")
            st.session_state["last_output"] = full_output
        else:
            st.error(f"❌ Agent failed with exit code {return_code}")
            st.code(full_output, language="text")
    
    # Display final summary if available
    st.divider()
    if state.get("final_summary"):
        st.markdown("### 📰 Latest Summary")
        st.markdown(state["final_summary"])
    else:
        st.info("No summary yet. Run the agent to see results.")


def render_summary_tab():
    """View latest summary."""
    state = read_state()
    summary = state.get("final_summary")
    
    if not summary:
        st.info("No summary yet. Run the agent after approving execution.")
        return
    
    st.markdown("### 📰 Latest Summary")
    st.markdown(summary)
    
    if state.get("chosen_skill_name"):
        st.caption(f"Generated by: **{state['chosen_skill_name']}**")


def render_raw_news_tab():
    """Display raw news items."""
    state = read_state()
    raw_news = state.get("raw_news") or []
    
    if not raw_news:
        st.info("No news fetched yet.")
        return
    
    st.markdown(f"### 📊 Raw News ({len(raw_news)} items)")
    
    for i, item in enumerate(raw_news, 1):
        with st.expander(f"{i}. {item.get('title', 'Untitled')[:60]}..."):
            st.markdown(f"**Title:** {item.get('title')}")
            st.markdown(f"**Source:** {item.get('source')}")
            st.markdown(f"**Summary:** {item.get('summary')}")
            if item.get("url"):
                st.markdown(f"[Read more]({item['url']})")


def render_skills_tab():
    """Browse available skills."""
    st.markdown("### 🛒 Skill Marketplace")
    
    if not SKILLS_DIR.exists():
        st.warning("Skills directory not found.")
        return
    
    skill_files = sorted(SKILLS_DIR.glob("*.json"))
    if not skill_files:
        st.info("No skills available.")
        return
    
    st.markdown(f"**Available Skills:** {len(skill_files)}")
    
    for skill_file in skill_files:
        try:
            skill_data = json.loads(skill_file.read_text(encoding="utf-8"))
            name = skill_data.get("name", "Unknown")
            description = skill_data.get("description", "No description")
            rating = skill_data.get("rating", 0)
            downloads = skill_data.get("downloads", 0)
            
            # Determine badge color
            if rating >= 4.8:
                badge = "🟢"
            elif rating >= 4.0:
                badge = "🟡"
            else:
                badge = "🔴"
            
            with st.expander(f"{badge} {name} ⭐{rating} ({downloads} downloads)"):
                st.markdown(f"**Description:** {description}")
                st.markdown(f"**Rating:** {rating}/5")
                st.markdown(f"**Downloads:** {downloads:,}")
                
                if "code" in skill_data:
                    st.code(skill_data["code"], language="python")
                if "instructions" in skill_data:
                    instructions = skill_data["instructions"]
                    # Try to decode base64
                    try:
                        import base64
                        decoded = base64.b64decode(instructions).decode()
                        st.info(f"📝 Instructions (decoded from base64):\n{decoded}")
                    except Exception:
                        st.code(instructions, language="text")
                
                if "signature" in skill_data:
                    st.caption(f"🔐 Signature: {skill_data['signature'][:16]}...")
        
        except Exception as e:
            st.error(f"Error loading {skill_file.name}: {e}")


def render_logs_tab():
    """View structured logs and metrics."""
    st.markdown("### 📊 Observability Dashboard")
    
    obs_col1, obs_col2 = st.columns([1, 1])
    
    with obs_col1:
        st.markdown("#### 📋 Recent Events")
        logs_df = load_jsonl_logs()
        
        if logs_df.empty:
            st.info("No logs yet.")
        else:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Events", len(logs_df))
            with col2:
                errors = len(logs_df[logs_df.get("event_type") == "error"]) if "event_type" in logs_df.columns else 0
                st.metric("Errors", errors)
            with col3:
                if "event_type" in logs_df.columns:
                    llm = len(logs_df[logs_df["event_type"] == "llm_call"])
                    st.metric("LLM Calls", llm)
            
            # Display events table
            display_cols = [col for col in ["timestamp", "event_type", "run_id"] if col in logs_df.columns]
            if display_cols:
                st.dataframe(
                    logs_df[display_cols].head(20),
                    width="stretch",
                    hide_index=True
                )
            csv_data = logs_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Logs (CSV)",
                data=csv_data,
                file_name="agent_logs.csv",
                mime="text/csv",
            )
    
    with obs_col2:
        st.markdown("#### 📈 Metrics")
        metrics_df = load_metrics_db()
        
        if metrics_df.empty:
            st.info("No metrics yet.")
        else:
            latest = metrics_df.iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tokens (Latest)", int(latest.get("total_tokens", 0)))
                st.metric("Duration (s)", f"{latest.get('total_duration_seconds', 0):.2f}")
            with col2:
                st.metric("Steps", int(latest.get("total_steps", 0)))
                st.metric("Errors", int(latest.get("total_errors", 0)))
            
            # Trends chart
            if len(metrics_df) > 1:
                metrics_df_sorted = metrics_df.sort_values("finished_at")
                fig = px.line(
                    metrics_df_sorted,
                    x="finished_at",
                    y="total_tokens",
                    title="Token Usage Trend",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)


def render_policy_tab():
    """Edit and view policies."""
    st.markdown("### ⚙️ Policy as Code")
    
    if POLICIES_FILE.exists():
        current_policy = POLICIES_FILE.read_text(encoding="utf-8")
    else:
        current_policy = "default_behavior: ask\nmax_steps: 10\nskills: []"
    
    edited_policy = st.text_area(
        "Edit policies.yaml",
        value=current_policy,
        height=300,
        help="YAML format. Saved policies take effect on the next agent run."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Policy", type="primary", width="stretch"):
            try:
                yaml.safe_load(edited_policy)
                POLICIES_FILE.write_text(edited_policy)
                st.success("✅ Policy saved successfully!")
            except yaml.YAMLError as e:
                st.error(f"❌ Invalid YAML: {e}")
    
    with col2:
        if st.button("🔄 Reload", width="stretch"):
            st.rerun()
    
    # Display parsed policy
    st.divider()
    try:
        parsed = yaml.safe_load(edited_policy)
        if parsed:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Default Behavior", parsed.get("default_behavior", "?").upper())
            with col2:
                st.metric("Max Steps", parsed.get("max_steps", "?"))
            with col3:
                num_skills = len(parsed.get("skills", []))
                st.metric("Configured Skills", num_skills)
            
            if parsed.get("skills"):
                st.markdown("**Skill Rules:**")
                for skill in parsed.get("skills", []):
                    allowed = "✅" if skill.get("allowed") else "❌"
                    req_approval = " 🔒" if skill.get("require_approval") else ""
                    st.caption(f"{allowed}{req_approval} {skill.get('name', 'Unknown')}")
    except yaml.YAMLError:
        st.warning("Invalid YAML syntax.")


def render_sidebar():
    """Sidebar with agent state and status."""
    state = read_state()
    
    st.sidebar.markdown("### 📊 Agent Status")
    
    # Display date and status in a card-like format
    display_date = state.get("date", date.today().isoformat())
    st.sidebar.markdown(f"""
    **Date:** `{display_date}`  
    **Status:** {"✅ Done" if state.get("done") else "⏳ Running"}
    """)
    
    if state.get("chosen_skill_name"):
        st.sidebar.caption(f"📌 **Selected Skill:** {state['chosen_skill_name']}")
    
    st.sidebar.divider()
    
    # Policy status
    st.sidebar.markdown("### 🔐 Policy Status")
    policies = load_policies()
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric(
            "Default",
            policies.get("default_behavior", "?").upper()
        )
    with col2:
        allowed_count = len([s for s in policies.get("skills", []) if s.get("allowed")])
        st.metric("Allowed Skills", allowed_count)


# ============================================================================
# Main App
# ============================================================================

def main():
    st.title("🛡️ AI News Agent – Supply Chain Security Demo")
    
    st.markdown(
        """
        **Security Research Project:** Demonstrates how marketplace skills can change agent behavior,
        and how signing, policy-as-code, sandboxing, and logging reduce supply-chain attack risk.
        """
    )
    
    render_sidebar()
    
    st.divider()
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🚀 Run Agent",
        "📰 Latest Summary",
        "📊 Raw News",
        "🛒 Skills",
        "📈 Observability",
        "⚙️ Policy",
    ])
    
    with tab1:
        render_run_tab()
    with tab2:
        render_summary_tab()
    with tab3:
        render_raw_news_tab()
    with tab4:
        render_skills_tab()
    with tab5:
        render_logs_tab()
    with tab6:
        render_policy_tab()


if __name__ == "__main__":
    main()
