"""
Chat interface API endpoints for FastAPI
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
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
from app.services.rag.agentic_rag_service import agentic_rag_service
from app.services.rag.multi_agent_service import multi_agent_service
from app.core.config import settings

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
            title=session_data.title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
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
                title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
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
        if query.use_agentic:
            # Use agentic RAG
            result = await agentic_rag_service.search(
                query=query.query,
                k=5,
                language=query.language,
                chat_history=chat_history
            )
        elif query.use_rag:
            # Use standard RAG
            result = await rag_service.generate_answer(
                query=query.query,
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
        session.updated_at = datetime.utcnow()

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
                "timestamp": datetime.utcnow().isoformat()
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
        session.updated_at = datetime.utcnow()

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
                "timestamp": datetime.utcnow().isoformat()
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
        session.updated_at = datetime.utcnow()

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
        session.updated_at = datetime.utcnow()

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

        # Messages today
        from datetime import date
        today = date.today()
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
                func.avg(ChatFeedback.score).label('avg_score')
            )
            .select_from(ChatFeedback)
            .where(ChatFeedback.user_id == current_user.id)
        )
        feedback = feedback_result.first()

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "messages_today": messages_today,
            "feedback_count": feedback.total if feedback else 0,
            "average_score": float(feedback.avg_score) if feedback and feedback.avg_score else None
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
        from datetime import timedelta
        from sqlalchemy import text

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Query daily message counts
        query = text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as message_count
            FROM chat_messages cm
            JOIN chat_sessions cs ON cm.session_id = cs.id
            WHERE cs.user_id = :user_id
                AND cm.created_at >= :start_date
                AND cm.created_at <= :end_date
            GROUP BY DATE(created_at)
            ORDER BY date
        """)

        result = await db.execute(query, {
            'user_id': current_user.id,
            'start_date': start_date,
            'end_date': end_date
        })

        activity_data = []
        for row in result:
            activity_data.append({
                'date': row.date.isoformat(),
                'messages': row.message_count
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": activity_data
        }

    except Exception as e:
        logger.error(f"Get activity data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))