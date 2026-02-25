"""
Conversation memory manager for maintaining context across chat messages.

Tracks conversation history, decisions, schemas used, and context
so the LLM can reference previous interactions.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.models.conversation import Conversation, Message
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConversationMemory:
    """Manages conversation history and context for LLM awareness."""
    
    MAX_HISTORY_TOKENS = 4000  # Approximate max tokens to include in context
    
    def __init__(self, conversation_id: str = None):
        """
        Initialize conversation memory.
        
        Args:
            conversation_id: ID of the conversation to load history from
        """
        self.conversation_id = conversation_id
        self.messages = []
        self.decisions = []  # Track made decisions
        self.schemas_mentioned = set()  # Tables/schemas referenced
        self.last_action = None
        self.context_summary = ""
        
        if conversation_id:
            self._load_conversation_history()
    
    def _load_conversation_history(self) -> bool:
        """
        Load all messages from a conversation.
        
        Returns:
            True if conversation found and loaded, False otherwise
        """
        try:
            from backend.models import db
            conv = db.session.get(Conversation, self.conversation_id)
            
            if not conv:
                logger.debug(f"[ConversationMemory] Conversation {self.conversation_id} not found")
                return False
            
            # Load messages in chronological order
            self.messages = sorted(conv.messages, key=lambda m: m.created_at)
            
            # Extract context from messages
            self._extract_context_from_history()
            
            logger.info(
                f"[ConversationMemory] ✓ Loaded {len(self.messages)} messages "
                f"for conversation {self.conversation_id}"
            )
            return True
        
        except Exception as e:
            logger.error(f"[ConversationMemory] Error loading history: {str(e)}")
            return False
    
    def _extract_context_from_history(self):
        """Extract context, decisions, and schemas from conversation history."""
        try:
            from backend.utils.schema_classifier import SchemaClassifier
            classifier = SchemaClassifier()
            
            for msg in self.messages:
                if not msg.content:
                    continue
                
                # Extract table names mentioned
                tables = classifier.extract_table_names(msg.content)
                self.schemas_mentioned.update(tables)
                
                # Track assistant responses and actions
                if msg.role == 'assistant':
                    if msg.action_data:
                        self.last_action = msg.action_data
                        self._extract_decision_from_action(msg.action_data)
            
            logger.debug(
                f"[ConversationMemory] Extracted: tables={self.schemas_mentioned}, "
                f"decisions={len(self.decisions)}, last_action={self.last_action is not None}"
            )
        
        except Exception as e:
            logger.error(f"[ConversationMemory] Error extracting context: {str(e)}")
    
    def _extract_decision_from_action(self, action: Dict[str, Any]):
        """Extract and track a decision from an action."""
        try:
            decision = {
                'type': action.get('type'),
                'confidence': action.get('confidence'),
                'sql_query': action.get('sql_query'),
                'timestamp': datetime.now().isoformat()
            }
            self.decisions.append(decision)
        except Exception as e:
            logger.debug(f"[ConversationMemory] Could not extract decision: {str(e)}")
    
    def get_conversation_context(self, max_messages: int = 10) -> str:
        """
        Get formatted conversation context for LLM.
        
        Returns the recent conversation history in a format suitable
        for inclusion in LLM prompts.
        
        Args:
            max_messages: Maximum number of recent messages to include
        
        Returns:
            Formatted conversation context string
        """
        if not self.messages:
            return ""
        
        # Get recent messages
        recent_messages = self.messages[-max_messages:]
        
        context_parts = []
        context_parts.append("=== CONVERSATION HISTORY ===")
        
        for msg in recent_messages:
            role = msg.role.upper()
            content = msg.content
            if len(content) > 200:
                content = content[:200] + "..."
            
            context_parts.append(f"\n{role}: {content}")
        
        context_parts.append("\n=== END HISTORY ===\n")
        
        return "\n".join(context_parts)
    
    def get_decisions_context(self) -> str:
        """
        Get formatted context of decisions made in conversation.
        
        Returns:
            Formatted decisions context
        """
        if not self.decisions:
            return ""
        
        context_parts = []
        context_parts.append("=== PREVIOUS DECISIONS ===")
        
        for i, decision in enumerate(self.decisions[-5:], 1):  # Last 5 decisions
            context_parts.append(f"\nDecision {i}:")
            context_parts.append(f"  Type: {decision.get('type')}")
            context_parts.append(f"  Confidence: {decision.get('confidence')}")
            if decision.get('sql_query'):
                query = decision.get('sql_query')
                if len(query) > 100:
                    query = query[:100] + "..."
                context_parts.append(f"  Query: {query}")
        
        context_parts.append("\n=== END DECISIONS ===\n")
        
        return "\n".join(context_parts)
    
    def get_schemas_context(self) -> str:
        """
        Get context about schemas mentioned in conversation.
        
        Returns:
            Formatted schemas context
        """
        if not self.schemas_mentioned:
            return ""
        
        schemas_list = ", ".join(sorted(self.schemas_mentioned))
        return f"In this conversation, we've been discussing: {schemas_list}\n"
    
    def get_full_context(self) -> str:
        """
        Get complete context for LLM including history, decisions, and schemas.
        
        Returns:
            Complete formatted context
        """
        context_parts = []
        
        schemas_ctx = self.get_schemas_context()
        if schemas_ctx:
            context_parts.append(schemas_ctx)
        
        decisions_ctx = self.get_decisions_context()
        if decisions_ctx:
            context_parts.append(decisions_ctx)
        
        history_ctx = self.get_conversation_context()
        if history_ctx:
            context_parts.append(history_ctx)
        
        return "\n".join(context_parts)
    
    def add_message(self, role: str, content: str, action_data: Dict = None):
        """
        Add a message to memory (for tracking current exchange).
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            action_data: Optional action data if assistant message
        """
        msg = {
            'role': role,
            'content': content,
            'action_data': action_data,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(msg)
        
        if action_data:
            self._extract_decision_from_action(action_data)
    
    def get_last_n_messages(self, n: int = 5) -> List[Dict]:
        """
        Get the last N messages from conversation.
        
        Args:
            n: Number of messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        class _MessageProxy:
            """Adapter that exposes both attribute and mapping access for a message.

            Allows tests and callers to use either `msg.content` or `msg['content']`.
            """
            def __init__(self, src):
                self._src = src

            def __getattr__(self, name):
                src = object.__getattribute__(self, '_src')
                if hasattr(src, name):
                    return getattr(src, name)
                if isinstance(src, dict) and name in src:
                    return src.get(name)
                raise AttributeError(name)

            def __getitem__(self, key):
                src = object.__getattribute__(self, '_src')
                if isinstance(src, dict):
                    return src[key]
                if hasattr(src, key):
                    return getattr(src, key)
                raise KeyError(key)

            def get(self, key, default=None):
                try:
                    return self.__getitem__(key)
                except Exception:
                    return default

        last_msgs = self.messages[-n:]
        # Wrap each message so callers can use attribute or dict-style access
        return [_MessageProxy(m) for m in last_msgs]
    
    def get_schemas_mentioned(self) -> set:
        """
        Get all schemas/tables mentioned in conversation.
        
        Returns:
            Set of table names
        """
        return self.schemas_mentioned.copy()
    
    def get_last_action(self) -> Optional[Dict]:
        """
        Get the last action suggested/executed in conversation.
        
        Returns:
            Last action dictionary or None
        """
        return self.last_action.copy() if self.last_action else None
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation state.
        
        Returns:
            Dictionary with conversation metadata
        """
        return {
            'conversation_id': self.conversation_id,
            'total_messages': len(self.messages),
            'total_decisions': len(self.decisions),
            'schemas_mentioned': list(self.schemas_mentioned),
            'last_action': self.last_action,
            'last_message_time': self.messages[-1].created_at.isoformat() if self.messages and hasattr(self.messages[-1], 'created_at') else None
        }
    
    def is_referencing_previous_context(self, query: str) -> bool:
        """
        Check if query is referencing previous conversation context.
        
        Args:
            query: User query
        
        Returns:
            True if query references previous discussion
        """
        reference_keywords = {
            'previous', 'before', 'earlier', 'that', 'those', 'last',
            'same', 'similar', 'again', 'also', 'too', 'check', 'review',
            'recall', 'remember', 'as we discussed', 'like before',
            'the one we', 'the data we', 'what we', 'chat', 'conversation',
            'needful', 'need', 'display', 'show', 'result', 'table'
        }
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in reference_keywords)
    
    def get_context_for_clarification(self, query: str) -> str:
        """
        Get helpful context when user query seems to reference previous discussion.
        
        Handles queries like:
        - "Check the chat and do the needful"
        - "Display the result in a table"
        - "What tables were we discussing?"
        
        Args:
            query: User query that may reference previous context
        
        Returns:
            Contextual information to help LLM understand reference
        """
        if not self.is_referencing_previous_context(query):
            return ""
        
        context_parts = []
        context_parts.append("\n" + "="*80)
        context_parts.append("[CONTEXT: User is referencing previous discussion]")
        context_parts.append("="*80)
        
        # Add tables we've been discussing
        if self.schemas_mentioned:
            context_parts.append(f"\nTables discussed in this conversation: {', '.join(sorted(self.schemas_mentioned))}")
        
        # Add the last query/action
        if self.last_action:
            context_parts.append(f"\n[LAST PREPARED ACTION]")
            context_parts.append(f"Type: {self.last_action.get('type')}")
            context_parts.append(f"Confidence: {self.last_action.get('confidence', 'unknown')}")
            if self.last_action.get('sql_query'):
                context_parts.append(f"SQL Query: {self.last_action.get('sql_query')}")
            if self.last_action.get('parameters'):
                context_parts.append(f"Parameters: {self.last_action.get('parameters')}")
        
        # Add recent conversation history
        if self.messages:
            context_parts.append(f"\n[RECENT CONVERSATION HISTORY]")
            for i, msg in enumerate(self.messages[-6:], 1):
                role_label = "USER" if msg.role == 'user' else "ASSISTANT"
                content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                if len(content) > 150:
                    content = content[:150] + "..."
                context_parts.append(f"{i}. {role_label}: {content}")
        
        context_parts.append("="*80 + "\n")
        
        return "\n".join(context_parts)

