"""
Chat summarization service for AIS-35.
Handles conversation history summarization to keep chats within token budgets.
"""
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from app.mongodb.models.chat import MongoChatSession, MongoChatMessage
from app.config import get_settings

settings = get_settings()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    Uses rough heuristic: 1 token ≈ 4 characters.
    
    For production, consider using tiktoken or model-specific tokenizers.
    """
    if not text:
        return 0
    return len(text) // 4


def should_summarize_session(
    messages: List[MongoChatMessage],
    context_limit: int = 32768,
    threshold_percent: float = 0.75,
    min_messages: int = 50
) -> bool:
    """
    Check if a session needs summarization based on:
    1. Total tokens > threshold_percent of context_limit
    2. Message count > min_messages
    
    Args:
        messages: List of chat messages
        context_limit: Model context window size (default 32K)
        threshold_percent: Trigger when history exceeds this % of limit
        min_messages: Minimum message count to consider summarization
        
    Returns:
        True if summarization should be triggered
    """
    if len(messages) < min_messages:
        return False
    
    total_tokens = sum(estimate_tokens(msg.content) for msg in messages)
    token_threshold = int(context_limit * threshold_percent)
    
    return total_tokens > token_threshold


async def create_summary(
    session: MongoChatSession,
    messages: List[MongoChatMessage],
    db: AsyncIOMotorDatabase,
    recent_message_count: int = 15,
    base_model_id: str = None
) -> Optional[str]:
    """
    Create a summary of conversation history.
    
    Strategy:
    - Keep last N messages verbatim (recent_message_count)
    - Summarize all messages before that window
    - Store summary and update session
    
    Args:
        session: Chat session to summarize
        messages: All messages in session (sorted by created_at)
        db: MongoDB database connection
        recent_message_count: How many recent messages to keep verbatim
        base_model_id: Model to use for summarization (defaults to base model)
        
    Returns:
        Generated summary text, or None if failed
    """
    if len(messages) <= recent_message_count:
        # Not enough messages to summarize
        return None
    
    # Split messages into "to summarize" and "keep recent"
    messages_to_summarize = messages[:-recent_message_count]
    boundary_message = messages_to_summarize[-1] if messages_to_summarize else None
    
    # Build conversation text for summarization
    conversation_text = ""
    for msg in messages_to_summarize:
        role_label = msg.role.upper()
        conversation_text += f"[{role_label}]: {msg.content}\n\n"
    
    # Construct summarization prompt
    prompt = f"""Summarize the following conversation history concisely but comprehensively.

Include:
1. Key topics and questions discussed
2. Important decisions or conclusions reached
3. Code, files, or systems mentioned (with paths/names)
4. Unresolved questions or pending items
5. Context needed for future messages

Provide a summary in 200-500 words that captures all essential context.

Conversation to summarize ({len(messages_to_summarize)} messages):

{conversation_text}

Summary:"""

    # Call LLM to generate summary
    try:
        # Resolve base model - we'll use the resolve_model_for_role from chat.py
        from app.api.chat import resolve_model_for_role
        
        if not base_model_id:
            base_model = await resolve_model_for_role(db, "base")
            if not base_model:
                return None
            base_model_id = base_model.get("_id")
        
        # Get model details and create provider
        from app.api.chat import _resolve_model
        provider_name, base_url, model_name, api_key = await _resolve_model(base_model_id, db)
        
        # Create LLM provider
        from app.llm.ollama import OllamaProvider
        from app.llm.openai_compatible import OpenAICompatibleProvider
        
        if provider_name == "ollama":
            provider = OllamaProvider(base_url=base_url, timeout=120.0)
        else:
            provider = OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key or "",
                timeout=120.0
            )
        
        # Generate summary
        from app.llm.base import Message, GenerationParams
        summary_response = await provider.chat(
            model_name=model_name,
            messages=[Message(role="user", content=prompt)],
            params=GenerationParams(
                temperature=0.3,  # Lower temp for more focused summary
                max_tokens=2000
            )
        )
        
        summary_text = summary_response.content.strip()
        
        # Update session with summary
        sessions_collection: AsyncIOMotorCollection = db["chat_sessions"]
        update_result = await sessions_collection.update_one(
            {"_id": session.id},
            {
                "$set": {
                    "summary": summary_text,
                    "summary_up_to_message_id": boundary_message.id if boundary_message else None,
                    "summary_created_at": datetime.utcnow().isoformat(),
                    "summary_token_count": estimate_tokens(summary_text),
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        return summary_text if update_result.modified_count > 0 else None
        
    except Exception as e:
        print(f"Error creating summary: {e}")
        return None


async def get_session_messages_for_llm(
    session: MongoChatSession,
    messages: List[MongoChatMessage],
    system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Build message history for LLM, including summary if present.
    
    Strategy:
    - Add system prompt (if provided)
    - Add summary as system message (if session has summary)
    - Add only messages AFTER the summarized portion
    
    Args:
        session: Chat session
        messages: All messages in session
        system_prompt: Optional system prompt to prepend
        
    Returns:
        List of message dicts ready for LLM input
    """
    history = []
    
    # Add system prompt
    if system_prompt:
        history.append({"role": "system", "content": system_prompt})
    
    # If session has summary, inject it as system message
    if session.summary and session.summary_up_to_message_id:
        summary_text = (
            f"**Previous conversation summary** (up to message {session.summary_up_to_message_id}):\n\n"
            f"{session.summary}"
        )
        history.append({"role": "system", "content": summary_text})
        
        # Only include messages AFTER the summarized portion
        recent_messages = [
            msg for msg in messages 
            if msg.created_at > session.summary_created_at
        ]
    else:
        # No summary, include all messages
        recent_messages = messages
    
    # Add recent messages
    for msg in recent_messages:
        if msg.role != "system":
            history.append({"role": msg.role, "content": msg.content})
    
    return history
