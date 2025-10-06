"""
Chat interface API endpoints for FastAPI
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.api.deps import get_current_user, get_optional_current_user, CurrentUser, OptionalUser
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, ChatFeedback, DocumentRequest, LinkRequest
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    ChatFeedbackRequest,
    ChatFeedbackResponse,
    DocumentRequestCreate,
    LinkRequestCreate,
    ChatHistoryResponse
)
from app.services.rag.rag_service import rag_service
from app.services.rag.multi_agent_service import multi_agent_service
from app.core.config import settings
from app.core.timezone_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new chat session"""
    try:
        session = ChatSession(
            user_id=current_user.id,
            title=session_data.title or f"Chat {utc_now().strftime('%Y-%m-%d %H:%M')}",
            context=session_data.context,
            language=session_data.language,
            agent_type=session_data.agent_type,
            is_active=True
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(f"Created chat session {session.id} for user {current_user.id}")

        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            context=session.context,
            language=session.language,
            agent_type=session.agent_type,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_message_at=session.last_message_at,
            message_count=0,
            is_active=session.is_active
        )

    except Exception as e:
        logger.error(f"Create session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_async_db)
):
    """List user's chat sessions"""
    try:
        # If no user authenticated, return empty list
        if not current_user:
            return ChatSessionListResponse(
                sessions=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
        # Build query
        query = select(ChatSession).where(ChatSession.user_id == current_user.id)

        if active_only:
            query = query.where(ChatSession.is_active == True)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(ChatSession.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        sessions = result.scalars().all()

        # Count messages for each session
        session_list = []
        for session in sessions:
            msg_count_result = await db.execute(
                select(func.count()).select_from(ChatMessage)
                .where(ChatMessage.session_id == session.id)
            )
            message_count = msg_count_result.scalar()

            session_list.append(ChatSessionResponse(
                id=session.id,
                user_id=session.user_id,
                title=session.title,
                context=session.context,
                language=session.language,
                agent_type=session.agent_type,
                created_at=session.created_at,
                updated_at=session.updated_at,
                last_message_at=session.last_message_at,
                message_count=message_count,
                is_active=session.is_active
            ))

        return ChatSessionListResponse(
            sessions=session_list,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"List sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Duplicate endpoint removed - using create_chat_session above


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: int,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db)
):
    """Get chat history for a session"""
    try:
        # Get session
        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get total message count
        count_result = await db.execute(
            select(func.count()).select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id)
        )
        total_messages = count_result.scalar()

        # Get messages with feedback eager loading
        messages_result = await db.execute(
            select(ChatMessage)
            .options(selectinload(ChatMessage.feedback))
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        messages = messages_result.scalars().all()

        # Format response
        message_list = []
        for msg in reversed(messages):  # Reverse to get chronological order
            # Get feedback data from relationship if it exists
            feedback_score = None
            feedback_text = None
            if msg.feedback:
                # Convert rating to score (positive=5, negative=1, or based on rating)
                feedback_score = 5 if msg.feedback.rating == 'positive' else 1
                feedback_text = msg.feedback.comment

            message_list.append(ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                content=msg.content,
                message_type=msg.message_type,
                created_at=msg.created_at,
                metadata=msg.message_metadata,
                feedback_score=feedback_score,
                feedback_text=feedback_text
            ))

        return ChatHistoryResponse(
            session=ChatSessionResponse(
                id=session.id,
                user_id=session.user_id,
                title=session.title,
                context=session.context,
                language=session.language,
                agent_type=session.agent_type,
                created_at=session.created_at,
                updated_at=session.updated_at,
                last_message_at=session.last_message_at,
                message_count=total_messages,
                is_active=session.is_active
            ),
            messages=message_list,
            has_more=(offset + limit) < total_messages,
            total_messages=total_messages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(
    query: ChatQueryRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Send a chat query and get response

    Uses RAG/Agentic RAG to generate responses
    """
    try:
        # Get or create session
        if query.session_id:
            session_result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == query.session_id,
                    ChatSession.user_id == current_user.id
                )
            )
            session = session_result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Create new session
            session = ChatSession(
                user_id=current_user.id,
                title=f"Chat {utc_now().strftime('%Y-%m-%d %H:%M')}",
                language=query.language,
                is_active=True
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        # Save user message
        user_message = ChatMessage(
            session_id=session.id,
            content=query.query,
            message_type='user',
            message_metadata={'language': query.language}
        )
        db.add(user_message)
        await db.commit()

        # If this is the first message in the session, update title from user message
        if session.title.startswith("Chat ") and " " in session.title:
            # Extract first 30 characters and add date
            first_words = query.query[:30].strip()
            if len(query.query) > 30:
                first_words += "..."
            current_date = utc_now().strftime('%d/%m/%Y')
            session.title = f"{first_words} [{current_date}]"
            await db.commit()

        # Get chat history for context
        history_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        history = history_result.scalars().all()

        chat_history = []
        for msg in reversed(history[:-1]):  # Exclude current message
            chat_history.append({
                'role': 'user' if msg.message_type == 'user' else 'assistant',
                'content': msg.content
            })

        # Generate response
        if query.use_rag:
            # Use mode from request, or determine based on use_agentic flag
            if hasattr(query, 'mode') and query.mode:
                mode = query.mode
            else:
                mode = "deep" if query.use_agentic else "auto"

            # Use unified RAG service
            result = await rag_service.generate_answer(
                query=query.query,
                mode=mode,
                context_size=5,
                max_tokens=query.max_tokens,
                temperature=query.temperature,
                language=query.language,
                db=db
            )
        else:
            # Use multi-agent without RAG
            result = await multi_agent_service.process_query(
                query=query.query,
                chat_history=chat_history,
                user_language=query.language
            )

        # Save assistant response
        assistant_message = ChatMessage(
            session_id=session.id,
            content=result.get('answer', result.get('response', '')),
            message_type='assistant',
            message_metadata={
                'llm_provider': result.get('llm_provider', 'unknown'),
                'agent_used': result.get('agent_used'),
                'response_time_ms': result.get('response_time_ms')
            }
        )
        db.add(assistant_message)

        # Update session
        session.updated_at = utc_now()
        session.last_message_at = utc_now()

        await db.commit()
        await db.refresh(assistant_message)

        logger.info(f"Chat query processed: session={session.id}, message={assistant_message.id}")

        # Get agent emoji
        agent_type = result.get('agent_used', 'knight')
        agent_emojis = {
            'knight': '⚔️',
            'wizard': '🧙‍♂️',
            'bard': '🎭'
        }

        return ChatQueryResponse(
            session_id=session.id,
            session_title=session.title,
            message={
                "id": str(assistant_message.id),
                "type": "assistant",
                "content": assistant_message.content,
                "timestamp": utc_now().isoformat()
            },
            user_message={
                "id": str(user_message.id),
                "type": "user",
                "content": user_message.content,
                "timestamp": user_message.created_at.isoformat()
            },
            context_used=len(result.get('sources', [])) > 0,
            response_time=result.get('response_time_ms', 0),
            useful_links=result.get('useful_links', []),
            downloadable_documents=result.get('downloadable_documents', []),
            agent_type=agent_type,
            agent_emoji=agent_emojis.get(agent_type, '🤖'),
            is_multi_agent=result.get('is_multi_agent', False),
            handoff_message=result.get('handoff_message')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def provide_feedback(
    feedback: ChatFeedbackRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Provide feedback for a chat message"""
    try:
        # Get message
        message_result = await db.execute(
            select(ChatMessage)
            .join(ChatSession)
            .where(
                ChatMessage.id == feedback.message_id,
                ChatSession.user_id == current_user.id
            )
        )
        message = message_result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Create feedback record (no need to update message directly)
        # Convert score to rating (1-2 = negative, 3-5 = positive)
        rating = ChatFeedback.RATING_POSITIVE if feedback.score >= 3 else ChatFeedback.RATING_NEGATIVE

        feedback_record = ChatFeedback(
            message_id=feedback.message_id,
            user_id=current_user.id,
            rating=rating,
            comment=feedback.text or ""
        )
        db.add(feedback_record)

        await db.commit()
        await db.refresh(feedback_record)

        logger.info(f"Feedback provided: message={feedback.message_id}, score={feedback.score}")

        return ChatFeedbackResponse(
            success=True,
            message_id=feedback.message_id,
            feedback_id=feedback_record.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a chat session"""
    try:
        # Get session
        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Soft delete (mark as inactive)
        session.is_active = False
        session.updated_at = utc_now()

        await db.commit()

        logger.info(f"Session deleted: {session_id}")

        return {"success": True, "message": "Session deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    WebSocket endpoint for real-time chat

    Requires authentication token in query params or headers
    """
    await websocket.accept()

    try:
        # TODO: Implement proper WebSocket authentication
        # For now, accept all connections

        logger.info(f"WebSocket connected: session={session_id}")

        while True:
            # Receive message
            data = await websocket.receive_json()

            # Process message
            response = {
                "type": "message",
                "content": f"Echo: {data.get('message', '')}",
                "timestamp": utc_now().isoformat()
            }

            # Send response
            await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


@router.post("/sessions/{session_id}/clear")
async def clear_chat_history(
    session_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Clear chat history for a session"""
    try:
        # Verify session ownership
        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete all messages
        await db.execute(
            ChatMessage.__table__.delete().where(ChatMessage.session_id == session_id)
        )

        # Update session
        session.updated_at = utc_now()

        await db.commit()

        logger.info(f"Chat history cleared: session={session_id}")

        return {"success": True, "message": "Chat history cleared"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages")
async def send_message(
    message_data: ChatMessageCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Send a message and get AI response
    Legacy endpoint for compatibility - redirects to /query
    """
    from app.schemas.chat import ChatQueryRequest

    query_request = ChatQueryRequest(
        session_id=message_data.session_id if hasattr(message_data, 'session_id') else None,
        query=message_data.content,
        use_rag=True,
        use_agentic=False,
        language=message_data.language if hasattr(message_data, 'language') else 'pt',
        temperature=0.7,
        max_tokens=1000
    )

    return await chat_query(query_request, db, current_user)


@router.put("/sessions/{session_id}/title")
async def update_session_title(
    session_id: int,
    title_data: Dict[str, str],
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Update chat session title"""
    try:
        # Get session
        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update title
        session.title = title_data.get('title', session.title)
        session.updated_at = utc_now()

        await db.commit()
        await db.refresh(session)

        logger.info(f"Session title updated: {session_id}")

        return {
            "success": True,
            "session_id": session.id,
            "title": session.title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update title error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_chat_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_async_db)
):
    """Get chat usage statistics"""
    try:
        # Total sessions
        sessions_result = await db.execute(
            select(func.count()).select_from(ChatSession)
            .where(ChatSession.user_id == current_user.id)
        )
        total_sessions = sessions_result.scalar()

        # Active sessions
        active_result = await db.execute(
            select(func.count()).select_from(ChatSession)
            .where(
                ChatSession.user_id == current_user.id,
                ChatSession.is_active == True
            )
        )
        active_sessions = active_result.scalar()

        # Total messages
        messages_result = await db.execute(
            select(func.count()).select_from(ChatMessage)
            .join(ChatSession)
            .where(ChatSession.user_id == current_user.id)
        )
        total_messages = messages_result.scalar()

        # Messages today (in UTC)
        from datetime import date
        today = utc_now().date()
        today_result = await db.execute(
            select(func.count()).select_from(ChatMessage)
            .join(ChatSession)
            .where(
                ChatSession.user_id == current_user.id,
                func.date(ChatMessage.created_at) == today
            )
        )
        messages_today = today_result.scalar()

        # Feedback stats
        feedback_result = await db.execute(
            select(
                func.count().label('total'),
                func.sum(
                    case(
                        (ChatFeedback.rating == ChatFeedback.RATING_POSITIVE, 1),
                        else_=0
                    )
                ).label('positive_count')
            )
            .select_from(ChatFeedback)
            .where(ChatFeedback.user_id == current_user.id)
        )
        feedback = feedback_result.first()

        # Calculate satisfaction rate (percentage of positive feedback)
        satisfaction_rate = None
        if feedback and feedback.total > 0:
            satisfaction_rate = (feedback.positive_count / feedback.total) * 100

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "messages_today": messages_today,
            "feedback_count": feedback.total if feedback else 0,
            "average_score": satisfaction_rate  # Now returns percentage of positive feedback
        }

    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity")
async def get_activity_chart_data(
    current_user: CurrentUser,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_async_db)
):
    """Get chat activity data for charts"""
    try:
        from datetime import timedelta, date as date_type
        from sqlalchemy import text

        end_date = utc_now()
        start_date = end_date - timedelta(days=days)

        # Query daily message counts
        messages_query = text("""
            SELECT
                DATE(cm.created_at) as date,
                COUNT(DISTINCT cs.id) as session_count
            FROM chat_messages cm
            JOIN chat_sessions cs ON cm.session_id = cs.id
            WHERE cs.user_id = :user_id
                AND cm.created_at >= :start_date
                AND cm.created_at <= :end_date
            GROUP BY DATE(cm.created_at)
            ORDER BY date
        """)

        messages_result = await db.execute(messages_query, {
            'user_id': current_user.id,
            'start_date': start_date,
            'end_date': end_date
        })

        # Query daily document uploads
        documents_query = text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as document_count
            FROM documents
            WHERE uploaded_by_id = :user_id
                AND created_at >= :start_date
                AND created_at <= :end_date
            GROUP BY DATE(created_at)
            ORDER BY date
        """)

        documents_result = await db.execute(documents_query, {
            'user_id': current_user.id,
            'start_date': start_date,
            'end_date': end_date
        })

        # Create dicts of actual activity
        messages_dict = {}
        for row in messages_result:
            messages_dict[row.date.isoformat()] = row.session_count

        documents_dict = {}
        for row in documents_result:
            documents_dict[row.date.isoformat()] = row.document_count

        # Generate complete date range with zeros for missing days
        activity_data = []
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            date_str = current_date.isoformat()
            activity_data.append({
                'date': date_str,
                'messages': messages_dict.get(date_str, 0),  # 0 for days without messages
                'documents': documents_dict.get(date_str, 0)  # 0 for days without documents
            })
            current_date += timedelta(days=1)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": activity_data
        }

    except Exception as e:
        logger.error(f"Get activity data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))