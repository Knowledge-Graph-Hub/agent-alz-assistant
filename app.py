#!/usr/bin/env python
"""agent-alz-assistant - Agentic AI assistant for Alzheimer's disease research with literature retrieval and knowledge synthesis"""

import asyncio
import os
from pathlib import Path

from nicegui import ui, app as nicegui_app
from dotenv import load_dotenv

from agent_alz_assistant.agent import ClaudeAgent

# Load environment variables
load_dotenv()

# Initialize agent
agent = ClaudeAgent()


class ChatMessage:
    """Container for a chat message"""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


# Store conversation history
conversation_history = []


@ui.page("/")
async def index():
    """Main chat interface"""

    ui.markdown("# agent-alz-assistant")
    ui.markdown("_Agentic AI assistant for Alzheimer's disease research with literature retrieval and knowledge synthesis_")

    # Sample questions
    with ui.row().classes("w-full max-w-4xl mx-auto gap-2 mb-4 flex-wrap"):
        ui.label("Sample questions:").classes("text-sm text-gray-600")
    
    sample_questions = [
        "What is APOE4 and how does it relate to Alzheimer's?",
        "What are the most accurate blood biomarkers for early AD detection?",
        "Explain the role of tau protein in Alzheimer's disease",
        "What is the amyloid cascade hypothesis?",
    ]

    # Chat container
    chat_container = ui.column().classes("w-full max-w-4xl mx-auto gap-4 mb-20")

    # Input area (fixed at bottom)
    with ui.footer().classes("bg-white"):
        with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
            user_input = ui.textarea(
                placeholder="Ask me anything...",
                on_change=lambda: None,
            ).classes("w-full").props("outlined autofocus")

            # Sample question buttons
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
    ui.run(
        title="agent-alz-assistant",
        port=8082,
        reload=False,
        show=True,
    )
