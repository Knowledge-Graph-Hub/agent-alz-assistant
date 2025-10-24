#!/usr/bin/env python
"""agent-alz-assistant - Agentic AI assistant for Alzheimer's disease research with literature retrieval and knowledge synthesis"""

import asyncio
import bcrypt
import os
import sys
import shutil
from pathlib import Path

from nicegui import ui, app as nicegui_app
from dotenv import load_dotenv

from agent_alz_assistant.agent import ClaudeAgent

# Load environment variables
load_dotenv()

# Clean up stale NiceGUI storage to prevent session issues
# This is important when restarting the app
NICEGUI_STORAGE = Path(".nicegui")
if NICEGUI_STORAGE.exists() and os.getenv("CLEAN_STORAGE", "true").lower() == "true":
    print(f"[INFO] Cleaning stale NiceGUI storage at {NICEGUI_STORAGE}")
    try:
        shutil.rmtree(NICEGUI_STORAGE)
        print("[INFO] Storage cleaned successfully")
    except Exception as e:
        print(f"[WARNING] Could not clean storage: {e}")

# Clean up old plot files on restart
PLOTS_DIR = Path("static/plots")
if PLOTS_DIR.exists() and os.getenv("CLEAN_PLOTS", "true").lower() == "true":
    print(f"[INFO] Cleaning old plots at {PLOTS_DIR}")
    try:
        for plot_file in PLOTS_DIR.glob("*.png"):
            plot_file.unlink()
        print("[INFO] Plots cleaned successfully")
    except Exception as e:
        print(f"[WARNING] Could not clean plots: {e}")

# Authentication settings
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"
PASSWORD_HASH = os.getenv("APP_PASSWORD_HASH", "").encode()

if DISABLE_AUTH:
    print("[WARNING] Authentication is DISABLED! Anyone can access this app.")
    print("[WARNING] Set DISABLE_AUTH=false in .env to re-enable authentication.")

# Get storage secret from environment (required for security)
STORAGE_SECRET = os.getenv("STORAGE_SECRET")
if not STORAGE_SECRET:
    raise ValueError("STORAGE_SECRET must be set in .env file - see .env.example")

# Get port from environment (required)
PORT = os.getenv("PORT")
if not PORT:
    raise ValueError("PORT must be set in .env file - see .env.example")
PORT = int(PORT)

# Initialize agent
agent = ClaudeAgent()


class ChatMessage:
    """Container for a chat message"""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


# Store conversation history
conversation_history = []


def check_password(password: str) -> bool:
    """Check if password matches the hash"""
    if not PASSWORD_HASH:
        return True  # No password set, allow access
    try:
        return bcrypt.checkpw(password.encode(), PASSWORD_HASH)
    except Exception as e:
        print(f"[ERROR] Password check failed: {e}")
        return False


@ui.page("/login")
async def login():
    """Login page"""
    def try_login():
        if check_password(password_input.value):
            nicegui_app.storage.user["authenticated"] = True
            ui.navigate.to("/")
        else:
            ui.notify("Invalid password", color="negative")
            password_input.value = ""

    with ui.column().classes("absolute-center items-center"):
        ui.markdown("# agent-alz-assistant")
        ui.markdown("_Alzheimer's Disease Research Assistant_")
        password_input = ui.input("Password", password=True, password_toggle_button=True).classes("w-64").on("keydown.enter", try_login)
        ui.button("Login", on_click=try_login).classes("w-64")


@ui.page("/")
async def index():
    """Main chat interface"""

    # Check authentication (skip if disabled)
    if not DISABLE_AUTH and not nicegui_app.storage.user.get("authenticated", False):
        ui.navigate.to("/login")
        return

    # Header
    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.markdown("# agent-alz-assistant")
        ui.markdown("_Agentic AI assistant for Alzheimer's disease research with literature retrieval and knowledge synthesis_")

    sample_questions = [
        "What is APOE4 and how does it relate to Alzheimer's?",
        "What are the most accurate blood biomarkers for early AD detection?",
        "Explain the role of tau protein in Alzheimer's disease",
        "Create a plot summarizing diagnostic accuracy of tests for Alzheimer's disease",
    ]

    # Chat container with bottom padding to prevent overlap with footer
    chat_container = ui.column().classes("w-full max-w-4xl mx-auto gap-4 p-4").style("min-height: 0; padding-bottom: 10px")

    # Input area (fixed at bottom)
    with ui.footer().classes("bg-white"):
        with ui.column().classes("w-full max-w-4xl mx-auto p-2"):
            user_input = ui.textarea(
                placeholder="Ask me anything...",
                on_change=lambda: None,
            ).classes("w-full").props("outlined autofocus rows=2")

            # Sample questions label and buttons
            ui.label("Sample questions:").classes("text-sm text-gray-600 mt-2")
            with ui.row().classes("w-full gap-2 flex-wrap"):
                for question in sample_questions:
                    ui.button(
                        question,
                        on_click=lambda q=question: user_input.set_value(q)
                    ).props("dense flat color=primary").classes("text-xs normal-case")

            async def send_message():
                """Send user message and get agent response"""
                query = user_input.value
                if not query.strip():
                    return

                # Clear input
                user_input.value = ""

                # Add user message to UI
                with chat_container:
                    with ui.row().classes("w-full justify-end"):
                        ui.chat_message(
                            text=query, name="You", sent=True
                        ).classes("bg-blue-100")

                # Add user message to history
                conversation_history.append(ChatMessage("user", query))

                # Show thinking indicator
                with chat_container:
                    thinking = ui.chat_message(
                        text="Thinking...", name="Assistant", sent=False
                    ).classes("bg-gray-100")

                # Get response from agent
                try:
                    response = await agent.chat(query, conversation_history)

                    # Remove thinking indicator
                    chat_container.remove(thinking)

                    # Add assistant response with markdown rendering
                    with chat_container:
                        with ui.chat_message(name="Assistant", sent=False).classes("bg-green-100"):
                            ui.markdown(response)

                    # Add to history
                    conversation_history.append(ChatMessage("assistant", response))

                except Exception as e:
                    chat_container.remove(thinking)
                    with chat_container:
                        ui.chat_message(
                            text=f"Error: {str(e)}", name="System", sent=False
                        ).classes("bg-red-100")

            ui.button("Send", on_click=send_message).classes("w-full").props(
                "color=primary"
            )


if __name__ in {"__main__", "__mp_main__"}:
    # Serve static files for plots
    nicegui_app.add_static_files('/static', 'static')

    ui.run(
        title="agent-alz-assistant",
        port=PORT,
        reload=False,
        show=True,
        storage_secret=STORAGE_SECRET,
    )
