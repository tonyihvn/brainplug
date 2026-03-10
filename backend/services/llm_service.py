"""LLM service for processing prompts."""
import os
import json
import uuid
import time
from datetime import datetime
try:
    import google.generativeai as genai
except Exception:
    genai = None
try:
    import anthropic
except Exception:
    anthropic = None
try:
    from openai import OpenAI as OpenAIClient
except Exception:
    OpenAIClient = None
try:
    import requests
except Exception:
    requests = None
from backend.models import db
from backend.models.conversation import Conversation, Message
from backend.utils.logger import setup_logger
from backend.utils.conversation_memory import ConversationMemory
from backend.utils.rag_database import RAGDatabase

logger = setup_logger(__name__)


class LLMService:
    """Service for LLM interactions."""
    
    def __init__(self):
        """Initialize LLM service."""
        self.model = None
        self.model_type = None
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.claude_client = None
        self.claude_model_id = None
        self.openai_client = None
        self.openai_model_id = None
        self.openai_api_key = None
        # Ollama local client settings - DO NOT auto-initialize
        self.ollama_host = None  # Will only be set if explicitly configured in DB
        self.ollama_model = None
        self.ollama_available = False
        self.active_db_query_mode = 'direct'  # Track active database query mode

        # Use RAG store as the canonical settings store for LLM models
        try:
            self.rag_db = RAGDatabase()
        except Exception:
            self.rag_db = None

        # Initialize from RAG Vector Database (the only settings source)
        try:
            self._ensure_active_model()
            self._load_active_database_mode()  # Load active database query mode
        except Exception as e:
            logger.warning(f"✗ Error initializing active LLM from RAG Vector Database: {str(e)}")
            # Note: SQL database is no longer used for settings - all settings come from RAG only
    
    def _load_active_database_mode(self):
        """Load the query mode of the active database (direct or api)."""
        try:
            if not self.rag_db:
                self.active_db_query_mode = 'direct'  # Default to direct
                return
            
            # Get all database settings
            all_settings = self.rag_db.get_all_database_settings() or []
            db_settings = [s for s in all_settings if s.get('db_type')]
            
            # Find active database
            active_db = next((s for s in db_settings if s.get('is_active')), None)
            
            if active_db:
                self.active_db_query_mode = active_db.get('query_mode', 'direct')
                logger.info(f"✓ Loaded active database query mode: {self.active_db_query_mode}")
            else:
                self.active_db_query_mode = 'direct'  # Default to direct if no active DB
        except Exception as e:
            logger.debug(f"Error loading active database mode: {e}")
            self.active_db_query_mode = 'direct'  # Default to direct on error

    
    def _try_init_ollama(self):
        """Try to initialize local Ollama model as fallback."""
        try:
            if requests:
                # probe common hosts
                candidates = []
                if self.ollama_host:
                    candidates.append(self.ollama_host.rstrip('/'))
                candidates.extend(['http://localhost:11434', 'http://127.0.0.1:11434'])

                endpoints = ['/api/tags', '/models', '/api/models']
                for h in candidates:
                    if not h:
                        continue
                    for endpoint in endpoints:
                        try:
                            url = f"{h}{endpoint}"
                            resp = requests.get(url, timeout=2)
                        except Exception:
                            continue

                        if resp.status_code == 200:
                            try:
                                data = resp.json()
                                models = []
                                if isinstance(data, list):
                                    for m in data:
                                        if isinstance(m, dict) and 'name' in m:
                                            models.append(m['name'])
                                        elif isinstance(m, str):
                                            models.append(m)
                                elif isinstance(data, dict):
                                    if 'models' in data:
                                        for m in data.get('models', []):
                                            if isinstance(m, dict) and 'name' in m:
                                                models.append(m['name'])
                                            elif isinstance(m, str):
                                                models.append(m)
                                    elif 'tags' in data and isinstance(data.get('tags'), list):
                                        for t in data.get('tags', []):
                                            if isinstance(t, str):
                                                models.append(t)

                                if models:
                                    # pick first model
                                    self.ollama_available = True
                                    self.ollama_host = h
                                    self.ollama_model = models[0]
                                    # Normalize model id if it contains an 'ollama:' prefix
                                    try:
                                        if isinstance(self.ollama_model, str) and self.ollama_model.lower().startswith('ollama:'):
                                            self.ollama_model = self.ollama_model.split(':', 1)[1]
                                    except Exception:
                                        pass
                                    self.model_type = 'ollama'
                                    self.model = 'ollama'
                                    logger.info(f"Fallback: Initialized Ollama model: {self.ollama_model} @ {self.ollama_host}")
                                    return
                            except Exception:
                                continue
                    if self.ollama_available:
                        return
        except Exception as e:
            logger.debug(f"Ollama fallback probe failed: {str(e)}")
    
    def process_prompt(self, prompt, rag_context, business_rules, conversation_id=None):
        """
        Process a user prompt through LLM with RAG context.
        
        Args:
            prompt: User's natural language prompt
            rag_context: Retrieved context from RAG
            business_rules: Mandatory business rules
            conversation_id: ID of conversation (optional)
        
        Returns:
            Dictionary with LLM response and suggested action
        """
        try:
            # LOG: Confirm receipt of prompt from frontend
            logger.info(f"✓ RECEIVED PROMPT from frontend: '{prompt[:80]}...'")
            logger.info(f"  Conversation ID: {conversation_id or 'NEW'}")
            
            # Load or create conversation
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
                conv = Conversation(id=conversation_id, title=prompt[:100])
                db.session.add(conv)
                db.session.commit()
            
            # Load conversation memory to get context from previous messages
            memory = ConversationMemory(conversation_id)
            logger.info(f"[ConversationMemory] Loaded conversation history: {len(memory.messages)} messages")
            
            # Refresh active model in case settings changed while server is running
            try:
                self._ensure_active_model()
                logger.info(f"✓ Active LLM service refreshed: model_type={self.model_type}")
            except Exception as e:
                logger.warning(f"_ensure_active_model failed during process_prompt: {e}")

            # LOG: Which LLM is active
            logger.info(f"→ ACTIVE LLM: {self.model_type.upper() if self.model_type else 'NONE'}")
            if self.model_type == 'gemini':
                # Show partial API key for debugging
                key_display = '(NO KEY)' if not self.api_key else f"{self.api_key[:10]}...{self.api_key[-10:]}" if len(self.api_key) > 20 else self.api_key
                logger.info(f"  Provider: Google Gemini")
                logger.info(f"  API Key: {key_display}")
                logger.info(f"  Model object: {'LOADED' if self.model else 'NOT LOADED'}")
            elif self.model_type == 'claude':
                # Show partial API key for debugging
                key_display = '(NO KEY)' if not self.claude_api_key else f"{self.claude_api_key[:10]}...{self.claude_api_key[-10:]}" if len(self.claude_api_key) > 20 else self.claude_api_key
                logger.info(f"  Provider: Anthropic Claude")
                logger.info(f"  API Key: {key_display}")
                logger.info(f"  Model: {self.claude_model_id}")
                logger.info(f"  Client: {'CONNECTED' if self.claude_client else 'FAILED'}")
            elif self.model_type == 'ollama':
                logger.info(f"  Provider: Local Ollama")
                logger.info(f"  Host: {self.ollama_host}")
                logger.info(f"  Model: {self.ollama_model}")
                logger.info(f"  Available: {self.ollama_available}")
            elif self.model_type == 'openai':
                key_display = '(NO KEY)' if not self.openai_api_key else f"{self.openai_api_key[:10]}...{self.openai_api_key[-10:]}" if len(self.openai_api_key) > 20 else self.openai_api_key
                logger.info(f"  Provider: OpenAI")
                logger.info(f"  API Key: {key_display}")
                logger.info(f"  Model: {self.openai_model_id}")
                logger.info(f"  Client: {'CONNECTED' if self.openai_client else 'FAILED'}")
            else:
                logger.warning(f"  No LLM configured!")
            
            # Build prompt context
            system_prompt = self._build_system_prompt(business_rules)
            enriched_prompt = self._build_enriched_prompt(
                prompt, rag_context, business_rules, memory
            )
            
            # Determine which LLM to call and invoke it. Build a safe fallback if provider isn't available.
            response_text = None

            # Claude (Anthropic)
            if self.model_type == 'claude' and self.claude_client:
                logger.info("→ CALLING Claude API...")
                try:
                    message = self.claude_client.messages.create(
                        model=self.claude_model_id,
                        max_tokens=1024,
                        system=system_prompt,
                        messages=[{"role": "user", "content": enriched_prompt}]
                    )
                    response_text = message.content[0].text
                    logger.info(f"✓ Claude responded: {len(response_text)} chars")
                except Exception as e:
                    logger.error(f"✗ Claude API error: {str(e)}")
                    response_text = f"Error calling Claude API: {str(e)}"

            # Local Ollama
            elif self.model_type == 'ollama' and self.ollama_available:
                logger.info(f"→ CALLING Ollama at {self.ollama_host} (model: {self.ollama_model})...")
                try:
                    if requests and self.ollama_host and self.ollama_model:
                        post_endpoints = ['/api/generate', '/api/completions', '/chat', '/api/chat']
                        # Retry loop: try endpoints/payloads up to a small number of attempts
                        max_attempts = 2
                        attempt = 0
                        for ep in post_endpoints:
                            if attempt >= max_attempts:
                                break
                            try:
                                url = f"{self.ollama_host.rstrip('/')}{ep}"
                                logger.debug(f"  Trying Ollama endpoint: {url}")

                                # Normalize Ollama model id (strip optional 'ollama:' prefix)
                                normalized_model = self.ollama_model
                                try:
                                    if isinstance(normalized_model, str) and normalized_model.lower().startswith('ollama:'):
                                        normalized_model = normalized_model.split(':', 1)[1]
                                except Exception:
                                    pass

                                # Prepare payloads using normalized model id
                                payloads = [
                                    {'model': normalized_model or self.ollama_model, 'prompt': f"{system_prompt}\n\nUser Query: {enriched_prompt}", 'stream': False},
                                    {'model': normalized_model or self.ollama_model, 'messages': [{'role': 'user', 'content': enriched_prompt}], 'stream': False},
                                ]

                                for payload in payloads:
                                    try:
                                        logger.info(f"  → POST {url}")
                                        logger.info(f"     Payload: {str(payload)[:150]}...")
                                        resp = requests.post(url, json=payload, timeout=30)
                                        logger.info(f"     Status: {resp.status_code}")
                                    except requests.exceptions.Timeout as te:
                                        logger.warning(f"  ✗ Timeout (30s) on {url}: {str(te)}")
                                        resp = None
                                    except requests.exceptions.ConnectionError as ce:
                                        logger.warning(f"  ✗ Connection failed to {url}: {str(ce)}")
                                        resp = None
                                    except Exception as e:
                                        logger.warning(f"  ✗ Request error on {url}: {str(e)}")
                                        resp = None

                                    if not resp:
                                        logger.debug(f"     No response object returned")
                                        continue

                                    # Log non-200 responses at debug level with a bit more context
                                    if resp.status_code != 200:
                                        try:
                                            body_preview = resp.text[:800] if resp.text else ''
                                            logger.debug(f"  ✗ Ollama {ep} returned status {resp.status_code}: {body_preview}")
                                        except Exception:
                                            logger.debug(f"  ✗ Ollama {ep} returned status {resp.status_code} (no text)")

                                    if resp.status_code == 200:
                                        # Ollama may return streaming JSON objects (one per line).
                                        # Log the response length and a preview for debugging.
                                        try:
                                            body = resp.text or ''
                                            logger.info(f"  ✓ Got response (len={len(body)}) preview: {body[:200]}")
                                            # NEW: Log full raw response for debugging
                                            logger.info(f"  [RAW OLLAMA RESPONSE] Full body:\n{body}")
                                            logger.info(f"  [RAW OLLAMA RESPONSE] Status code: {resp.status_code}")
                                            logger.info(f"  [RAW OLLAMA RESPONSE] Headers: {dict(resp.headers)}")
                                        except Exception:
                                            logger.info(f"  ✓ Got response (could not read text)")

                                        try:
                                            response_text = self._extract_ollama_text(resp)
                                            logger.info(f"  ✓ Extracted text (len={len(response_text) if response_text else 0})")
                                            # NEW: Log what was extracted
                                            if response_text:
                                                logger.info(f"  [EXTRACTED] Text preview: {response_text[:300]}")
                                            else:
                                                logger.warning(f"  [EXTRACTED] Extraction returned None/empty")
                                        except Exception as e:
                                            logger.warning(f"  ✗ Failed to extract Ollama response: {str(e)}")
                                            response_text = None

                                        # If nothing usable returned, increment attempt and retry other payloads/endpoints
                                        if response_text:
                                            logger.info(f"✓ Ollama responded from {ep}: {len(response_text)} chars")
                                            break
                                        else:
                                            attempt += 1
                                            logger.debug(f"  Empty response_text; incrementing attempt to {attempt}")
                                    else:
                                        logger.warning(f"  ✗ Ollama {ep} returned status {resp.status_code}: {resp.text[:100]}")
                            except Exception as e:
                                logger.warning(f"  ✗ Error trying Ollama endpoint {ep}: {str(e)}")
                                continue
                        
                        if not response_text:
                            logger.warning('✗ Ollama endpoints did not return usable content; using fallback response')
                            response_text = ("UNDERSTANDING: Local Ollama model is not responding correctly.\n"
                                           "ACTION_TYPE: NONE\n"
                                           "SQL_QUERY: N/A\n"
                                           "PARAMETERS: N/A\n"
                                           "CONFIDENCE: low\n"
                                           "NEXT_STEP: Check if Ollama service is running on " + self.ollama_host)
                    else:
                        logger.error(f"✗ Missing required Ollama config: requests={bool(requests)} | host={self.ollama_host} | model={self.ollama_model}")
                        response_text = "Error: Ollama configuration incomplete"
                except Exception as e:
                    logger.error(f"✗ Error calling Ollama: {str(e)}", exc_info=True)
                    response_text = f"Error calling Ollama at {self.ollama_host}: {str(e)}"

            # Google Gemini
            elif self.model_type == 'gemini' and genai and self.api_key:
                logger.info("→ CALLING Google Gemini API...")
                try:
                    # If we already instantiated a GenerativeModel, use it. Otherwise require GEMINI_MODEL_ID env or DB model.
                    if self.model:
                        response = self.model.generate_content(f"{system_prompt}\n\nUser Query: {enriched_prompt}")
                        response_text = getattr(response, 'text', None) or (response if isinstance(response, str) else None)
                        logger.info(f"✓ Gemini responded: {len(response_text) if response_text else 0} chars")
                    else:
                        logger.warning("✗ Gemini API key present but model not instantiated")
                        response_text = ("UNDERSTANDING: The system has a GEMINI API key but no model is configured.\n"
                                         "ACTION_TYPE: NONE\n"
                                         "SQL_QUERY: N/A\n"
                                         "PARAMETERS: N/A\n"
                                         "CONFIDENCE: low\n"
                                         "NEXT_STEP: Configure a valid Gemini model_id in settings or set GEMINI_MODEL_ID in .env.")
                except Exception as e:
                    error_msg = str(e)
                    # Log which API key was used for debugging quota/rate limit issues
                    key_display = '(NO KEY)' if not self.api_key else f"{self.api_key[:10]}...{self.api_key[-10:]}" if len(self.api_key) > 20 else self.api_key
                    logger.error(f"✗ Gemini API error using key [{key_display}]: {error_msg}")
                    if '429' in error_msg or 'quota' in error_msg.lower() or 'rate' in error_msg.lower():
                        logger.error(f"  ⚠️  QUOTA/RATE LIMIT EXCEEDED - Check your Gemini API plan and billing")
                        response_text = f"Gemini API Error: {error_msg}. Your API quota may be exceeded."
                    else:
                        response_text = f"Error calling Gemini API: {error_msg}"

            # Anthropic Claude
            elif self.model_type == 'claude' and anthropic and self.claude_client:
                logger.info("→ CALLING Anthropic Claude API...")
                try:
                    message = self.claude_client.messages.create(
                        model=self.claude_model_id or 'claude-3-5-haiku-20241022',
                        max_tokens=2048,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": enriched_prompt}
                        ]
                    )
                    response_text = message.content[0].text if message.content else ""
                    logger.info(f"✓ Claude responded: {len(response_text) if response_text else 0} chars")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"✗ Claude API error: {error_msg}")
                    if '429' in error_msg or 'overloaded' in error_msg.lower():
                        logger.error(f"  ⚠️  RATE LIMIT EXCEEDED - Claude API is overloaded or rate limited")
                        response_text = f"Claude API Error: {error_msg}. API may be rate limited."
                    else:
                        response_text = f"Error calling Claude API: {error_msg}"

            # OpenAI GPT
            elif self.model_type == 'openai' and OpenAIClient and self.openai_client:
                logger.info(f"→ CALLING OpenAI API ({self.openai_model_id})...")
                try:
                    message = self.openai_client.chat.completions.create(
                        model=self.openai_model_id or 'gpt-4o',
                        max_tokens=2048,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": enriched_prompt}
                        ]
                    )
                    response_text = message.choices[0].message.content if message.choices else ""
                    logger.info(f"✓ OpenAI responded: {len(response_text) if response_text else 0} chars")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"✗ OpenAI API error: {error_msg}")
                    if '429' in error_msg or 'rate' in error_msg.lower():
                        logger.error(f"  ⚠️  RATE LIMIT EXCEEDED - OpenAI API is rate limited")
                        response_text = f"OpenAI API Error: {error_msg}. API may be rate limited."
                    elif 'insufficient_quota' in error_msg.lower() or 'quota' in error_msg.lower():
                        logger.error(f"  ⚠️  QUOTA EXCEEDED - Check your OpenAI account billing")
                        response_text = f"OpenAI API Error: {error_msg}. Check your API quota."
                    else:
                        response_text = f"Error calling OpenAI API: {error_msg}"

            # No model available
            else:
                # Check what went wrong
                if self.model_type == 'ollama':
                    logger.warning(f"✗ Ollama configured but not available: requests={bool(requests)} | host={self.ollama_host} | model={self.ollama_model} | available={self.ollama_available}")
                    response_text = f"Error: Local Ollama not responding. Check service is running at {self.ollama_host}"
                elif self.model_type == 'claude':
                    logger.warning(f"✗ Claude configured but client not initialized: client={bool(self.claude_client)} | model_id={self.claude_model_id}")
                    response_text = "Error: Claude client failed to initialize. Check API key is valid."
                elif self.model_type == 'openai':
                    logger.warning(f"✗ OpenAI configured but client not initialized: client={bool(self.openai_client)} | model_id={self.openai_model_id}")
                    response_text = "Error: OpenAI client failed to initialize. Check API key is valid."
                elif self.model_type == 'gemini':
                    logger.warning(f"✗ Gemini configured but model not loaded: api_key={bool(self.api_key)} | model={bool(self.model)}")
                    response_text = "Error: Gemini model failed to load. Check API key and model_id."
                else:
                    logger.warning("✗ NO LLM MODEL CONFIGURED - No model_type is set")
                    response_text = (
                        "UNDERSTANDING: The system is not currently configured with a cloud LLM.\n"
                        "ACTION_TYPE: NONE\n"
                        "SQL_QUERY: N/A\n"
                        "PARAMETERS: N/A\n"
                        "CONFIDENCE: low\n"
                        "NEXT_STEP: Configure LLM settings (Gemini, Claude, OpenAI, or local Ollama) with valid API key or model.")
            
            # Parse response to extract understanding, action, and SQL
            logger.info(f"→ PARSING LLM response...")
            parsed = self._parse_response(response_text) or {}
            parsed_explanation = parsed.get('explanation') if isinstance(parsed.get('explanation'), str) else (str(parsed.get('explanation') or '') )
            logger.info(f"✓ PARSED: action_type={parsed.get('action_type')} | explanation={parsed_explanation[:60] if parsed_explanation else 'None'}...")
            
            # Store user message
            user_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role='user',
                content=prompt
            )
            db.session.add(user_msg)
            
            # Store assistant response with action data
            assistant_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role='assistant',
                content=parsed.get('explanation') or '',
                action_data=parsed.get('action') or {}
            )
            db.session.add(assistant_msg)
            db.session.commit()
            
            logger.info(f"✓ COMPLETE: Conversation {conversation_id} updated with LLM response")
            
            return {
                'conversation_id': conversation_id,
                'explanation': parsed.get('explanation') or 'Unable to process request',
                'action': parsed.get('action') or {},
                'action_type': parsed.get('action_type'),
                'sql_query': parsed.get('sql_query'),
                'message_id': assistant_msg.id
            }
        
        except Exception as e:
            logger.error(f"✗ Error processing prompt: {str(e)}")
            raise

    def _ensure_active_model(self):
        """Ensure self reflects the currently active LLM model stored in the RAG settings store.

        This reads entries saved via `rag_db.save_setting('llm_<id>', model_dict)` and
        initializes the appropriate client (ollama/gemini/claude) for runtime use.
        """
        try:
            # Reset current runtime pointers
            self.model = None
            self.model_type = None
            self.ollama_available = False
            self.ollama_model = None
            self.ollama_host = None
            self.claude_client = None
            self.claude_model_id = None
            self.openai_client = None
            self.openai_model_id = None
            self.openai_api_key = None

            if not getattr(self, 'rag_db', None):
                logger.debug("_ensure_active_model: no rag_db available")
                return None

            # Retrieve all saved settings and filter LLM entries
            all_settings = self.rag_db.get_all_database_settings() or []
            try:
                # Temporary debug: dump the raw settings retrieved from the RAG store
                logger.debug(f"_ensure_active_model: retrieved {len(all_settings)} entries from rag_db.get_all_database_settings()")
                try:
                    raw_dump = json.dumps(all_settings, default=str)
                    logger.debug(f"_ensure_active_model: raw rag_db settings payload: {raw_dump}")
                except Exception as _jd:
                    logger.debug(f"_ensure_active_model: could not JSON-dump rag settings: {_jd}")
            except Exception:
                # ensure debug logging doesn't break initialization
                pass
            llm_settings = [s for s in all_settings if (str(s.get('id') or '').startswith('llm_') or s.get('model_type'))]

            # Normalize and pick active by priority
            active_candidates = [s for s in llm_settings if s.get('is_active')]
            if not active_candidates and llm_settings:
                # If none explicitly active, fall back to lowest priority
                try:
                    active_candidates = sorted(llm_settings, key=lambda x: x.get('priority', 999))[:1]
                except Exception:
                    active_candidates = [llm_settings[0]]

            active = active_candidates[0] if active_candidates else None

            if not active:
                logger.info("_ensure_active_model: no active LLM found in RAG store")
                return None

            logger.info(f"_ensure_active_model: found active LLM in RAG store: {active.get('name')}")
            model_type = (active.get('model_type') or '').lower()

            if model_type in ('ollama', 'local'):
                model_id = active.get('model_id')
                api_endpoint = active.get('api_endpoint')
                if model_id and api_endpoint:
                    self.ollama_model = model_id
                    self.ollama_host = api_endpoint
                    self.ollama_available = True
                    self.model_type = 'ollama'
                    logger.info(f"✓ Initialized Ollama from RAG: {self.ollama_model} @ {self.ollama_host}")
                    return active
                else:
                    logger.warning("_ensure_active_model: Ollama entry missing model_id or api_endpoint")

            if model_type in ('gemini', 'google'):
                gemini_api_key = active.get('api_key') or os.getenv('GEMINI_API_KEY')
                if genai and gemini_api_key:
                    try:
                        # IMPORTANT: Clear cached Google API credentials to avoid using old/expired keys
                        # The genai library caches credentials in module state, so we need to reset it
                        # before calling configure() with the new key
                        try:
                            # Force reload the genai module to clear any cached state
                            if hasattr(genai, '_client'):
                                delattr(genai, '_client')
                            logger.debug("_ensure_active_model: Cleared cached genai client state")
                        except Exception as cache_clear_err:
                            logger.debug(f"_ensure_active_model: Could not clear genai cache: {cache_clear_err}")
                        
                        # Configure with the current API key (from RAG or .env)
                        # This MUST happen after any cache clearing
                        logger.info(f"_ensure_active_model: Configuring Gemini with API key (preview: {gemini_api_key[:30]}...)")
                        genai.configure(api_key=gemini_api_key)
                        
                        model_id = active.get('model_id') or os.getenv('GEMINI_MODEL_ID')
                        if model_id:
                            self.model = genai.GenerativeModel(model_id)
                            self.model_type = 'gemini'
                            self.api_key = gemini_api_key
                            logger.info(f"✓ Initialized Gemini from RAG: {model_id}")
                            return active
                        else:
                            logger.warning("_ensure_active_model: Gemini entry missing model_id")
                    except Exception as e:
                        logger.error(f"_ensure_active_model: failed to init Gemini: {e}")
                        # Log to help users debug API key issues
                        if 'API key' in str(e) or 'expired' in str(e).lower():
                            logger.error(f"_ensure_active_model: Gemini API key issue detected. Check that your API key is valid and not expired.")
                        return None
                else:
                    if not genai:
                        logger.debug("_ensure_active_model: genai library not available")
                    if not gemini_api_key:
                        logger.debug("_ensure_active_model: No Gemini API key provided (not in RAG or .env)")

            if model_type in ('claude', 'anthropic'):
                claude_api_key = active.get('api_key') or os.getenv('LLM_CLAUDE_HAIKU_3.5_API_KEY')
                if anthropic and claude_api_key:
                    try:
                        self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
                        self.claude_model_id = active.get('model_id')
                        self.model_type = 'claude'
                        logger.info(f"✓ Initialized Claude from RAG: {self.claude_model_id}")
                        return active
                    except Exception as e:
                        logger.warning(f"_ensure_active_model: failed to init Claude: {e}")

            if model_type in ('gpt', 'openai'):
                openai_api_key = active.get('api_key') or os.getenv('OPENAI_API_KEY')
                if OpenAIClient and openai_api_key:
                    try:
                        self.openai_client = OpenAIClient(api_key=openai_api_key)
                        self.openai_model_id = active.get('model_id') or 'gpt-4o'
                        self.openai_api_key = openai_api_key
                        self.model_type = 'openai'
                        logger.info(f"✓ Initialized OpenAI from RAG: {self.openai_model_id}")
                        return active
                    except Exception as e:
                        logger.warning(f"_ensure_active_model: failed to init OpenAI: {e}")

            logger.warning("_ensure_active_model: found an LLM entry but could not initialize a client")
            return None
        except Exception as e:
            logger.error(f"_ensure_active_model error: {e}")
            return None
    
    # ============================================================================
    # DATABASE SCHEMA VALIDATION HELPERS
    # ============================================================================
    
    def _extract_schema_from_rag(self):
        """
        Extract available tables and columns from RAG database.
        Returns: dict with 'tables' (list of table names) and 'columns' (dict: table -> column list)
        """
        try:
            if not self.rag_db:
                return {'tables': [], 'columns': {}}
            
            # Get all business rules with meta_type='table_comprehensive'
            all_rules = self.rag_db.get_all_rules() or []
            
            schema_dict = {
                'tables': [],
                'columns': {}
            }
            
            for rule in all_rules:
                metadata = rule.get('metadata', {})
                if metadata.get('meta_type') == 'table_comprehensive':
                    # Extract table name from category format: "{db_id}_{table_name}"
                    category = metadata.get('category', '')
                    if category:
                        parts = category.rsplit('_', 1)
                        if len(parts) == 2:
                            table_name = parts[1]
                            schema_dict['tables'].append(table_name)
                            
                            # Extract columns from rule content (look for "Columns:" section)
                            content = rule.get('content', '')
                            columns = []
                            try:
                                # Parse columns from the "Columns:" section
                                if 'Columns:' in content:
                                    columns_start = content.index('Columns:') + len('Columns:')
                                    # Find next section header
                                    sections = ['FOREIGN KEY RELATIONSHIPS', 'RELATIONSHIPS', 'SCHEMA', 'SAMPLE DATA', 'BUSINESS RULE']
                                    columns_end = len(content)
                                    for section in sections:
                                        try:
                                            idx = content.index(section, columns_start)
                                            if idx > columns_start and idx < columns_end:
                                                columns_end = idx
                                        except ValueError:
                                            pass
                                    
                                    columns_text = content[columns_start:columns_end]
                                    
                                    # Extract column names (format: "  - column_name: type, ...")
                                    for line in columns_text.split('\n'):
                                        line = line.strip()
                                        if line.startswith('- '):
                                            col_name = line[2:].split(':')[0].split('(')[0].split('→')[0].strip()
                                            if col_name:
                                                columns.append(col_name)
                            except Exception as e:
                                logger.debug(f"Error parsing columns for {table_name}: {e}")
                            
                            schema_dict['columns'][table_name] = columns
            
            logger.info(f"[SCHEMA_VALIDATION] Extracted {len(schema_dict['tables'])} tables from RAG")
            return schema_dict
        
        except Exception as e:
            logger.error(f"Error extracting schema from RAG: {e}")
            return {'tables': [], 'columns': {}}
    
    def _extract_table_references(self, sql_query: str) -> set:
        """
        Extract table names from a SQL query.
        Returns: set of table names referenced in the query
        """
        import re
        
        if not sql_query:
            return set()
        
        try:
            # Normalize SQL
            sql = sql_query.upper()
            
            # Remove comments
            sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
            sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
            
            # Extract table references using regex patterns
            tables = set()
            
            # Pattern 1: FROM table_name or JOIN table_name
            pattern1 = r'\b(?:FROM|JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(pattern1, sql):
                table = match.group(1).lower()
                if table not in ('SELECT', 'WHERE', 'GROUP', 'ORDER', 'LIMIT', 'VALUES'):
                    tables.add(table)
            
            # Pattern 2: INTO table_name (INSERT)
            pattern2 = r'\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(pattern2, sql):
                tables.add(match.group(1).lower())
            
            # Pattern 3: UPDATE table_name
            pattern3 = r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(pattern3, sql):
                tables.add(match.group(1).lower())
            
            # Pattern 4: DELETE FROM table_name
            pattern4 = r'\bDELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(pattern4, sql):
                tables.add(match.group(1).lower())
            
            logger.debug(f"[SQL_VALIDATION] Extracted tables from SQL: {tables}")
            return tables
        
        except Exception as e:
            logger.warning(f"Error extracting table references from SQL: {e}")
            return set()
    
    def _validate_sql_against_schema(self, sql_query: str, available_tables: list) -> dict:
        """
        Validate that SQL query only uses available tables.
        
        Args:
            sql_query: SQL query to validate
            available_tables: List of valid table names
        
        Returns:
            dict with 'valid' (bool), 'invalid_tables' (set), and 'message' (str)
        """
        if not sql_query:
            return {'valid': True, 'invalid_tables': set(), 'message': 'No SQL query to validate'}
        
        try:
            referenced_tables = self._extract_table_references(sql_query)
            available_tables_lower = {t.lower() for t in available_tables}
            
            invalid_tables = referenced_tables - available_tables_lower
            
            if invalid_tables:
                message = f"SQL references non-existent tables: {', '.join(sorted(invalid_tables))}"
                logger.warning(f"[SQL_VALIDATION] FAILED: {message}")
                return {
                    'valid': False,
                    'invalid_tables': invalid_tables,
                    'message': message
                }
            
            logger.info(f"[SQL_VALIDATION] PASSED: All referenced tables are valid")
            return {
                'valid': True,
                'invalid_tables': set(),
                'message': 'SQL query is valid'
            }
        
        except Exception as e:
            logger.error(f"Error validating SQL: {e}")
            return {
                'valid': False,
                'invalid_tables': set(),
                'message': f'Validation error: {str(e)}'
            }
    
    def _build_system_prompt(self, business_rules):
        """Build system prompt with business rules and database schema constraints."""
        # Handle None value for business_rules
        if business_rules is None:
            business_rules = []
        
        rules_text = "\n".join([
            f"- {rule['content']}" 
            for rule in business_rules if rule.get('is_active')
        ])
        
        # Extract schema from RAG for constraint enforcement
        schema = self._extract_schema_from_rag()
        available_tables = schema.get('tables', [])
        
        # Build database constraints section
        constraint_section = ""
        if available_tables:
            tables_list = ", ".join(sorted(available_tables))
            constraint_section = f"""
════════════════════════════════════════════════════════════════
⚠️  CRITICAL: DATABASE STRUCTURE ENFORCEMENT
════════════════════════════════════════════════════════════════

You MUST ONLY suggest SQL queries that use the following tables:
{tables_list}

CRITICAL RULES:
1. ONLY reference tables listed above in SQL queries
2. If a user asks for data from a table NOT in the list above, respond with:
   "I cannot suggest a query for that table because it does not exist in the connected database."
3. Always validate that table names exist before suggesting queries
4. If you cannot fulfill a request with available tables, explain why
5. NEVER invent or assume table names - only use what's listed above

If user requests data from tables not in the list, respond clearly:
- What the user asked for
- Which table(s) they requested
- Why it's not available (not in connected database)
- What alternative tables might contain similar data (if any)
"""
        
        return f"""You are an intelligent assistant that understands natural language prompts 
and takes actions on behalf of users. 

IMPORTANT: You MUST maintain awareness of the conversation history provided below. 
When users reference "the chat", "previous", "that query", "check", or similar terms, 
they are referring to earlier messages in THIS CONVERSATION. Always look back at the conversation 
history to understand context and make decisions.

{constraint_section}

BUSINESS RULES (MANDATORY):
{rules_text}

POSSIBLE ACTIONS:
1. Database Query - Extract structured data from connected databases
2. Email Actions - Read/write emails using known contacts and data
3. URL Reading - Read and summarize web content
4. API Calls - Interact with external APIs
5. Scheduled Activities - Schedule tasks for later execution
6. Reports - Generate reports from accumulated data

CRITICAL RULES FOR CONTEXT AWARENESS:
- If user says "check the chat" or "review previous", look at the conversation history
- If user says "display the result in a table", remember the last query and format appropriately
- If user says "do the needful", understand what action was being prepared or discussed
- If user mentions a table/data but you don't see it in current prompt, check conversation history
- If user references numbers, categories, or queries from earlier, use that context
- Never say you don't have context if it's available in conversation history

For each prompt, you MUST:
1. Check conversation history for context
2. Explain what you understand from the user's request (including historical context)
3. Identify which action(s) are needed
4. If it's a database action, provide the SQL query
5. Extract parameters needed for the action
6. NEVER ask for clarification if the information is available in conversation history
7. VALIDATE that all tables in SQL queries exist in the connected database

Format your response as:
UNDERSTANDING: [What you understand, including reference to prior context if applicable]
ACTION_TYPE: [Type of action]
SQL_QUERY: [If applicable, the SQL query]
PARAMETERS: [Required parameters]
CONFIDENCE: [Your confidence level - low/medium/high]
NEXT_STEP: [What will happen if user confirms]"""
    
    def _build_enriched_prompt(self, prompt, rag_context, business_rules, memory=None):
        """
        Build enriched prompt with RAG context and conversation memory.
        
        Args:
            prompt: User's current prompt
            rag_context: RAG-retrieved schema context (list or None)
            business_rules: Applicable business rules (list or None)
            memory: ConversationMemory instance with history
        
        Returns:
            Enriched prompt string for LLM
        """
        # Handle None values for rag_context and business_rules
        if rag_context is None:
            rag_context = []
        if business_rules is None:
            business_rules = []
        
        context_text = "\n".join([
            f"- {item}" for item in rag_context[:5]
        ])
        
        rules_text = "\n".join([
            f"- {rule['content']}" 
            for rule in business_rules if rule.get('rule_type') == 'compulsory'
        ])
        
        # Build comprehensive conversation memory context
        memory_context = ""
        if memory:
            memory_parts = []
            
            # Add full conversation history
            history = memory.get_conversation_context(max_messages=10)
            if history:
                memory_parts.append(history)
            
            # Add previous decisions made
            decisions = memory.get_decisions_context()
            if decisions:
                memory_parts.append(decisions)
            
            # Add schemas/tables discussed
            schemas = memory.get_schemas_context()
            if schemas:
                memory_parts.append(schemas)
            
            # Add clarification context for referenced queries
            clarification = memory.get_context_for_clarification(prompt)
            if clarification:
                memory_parts.append(clarification)
            
            # Add last action details
            if memory.last_action:
                memory_parts.append(
                    f"\n[LAST ACTION]\n"
                    f"Type: {memory.last_action.get('type')}\n"
                    f"SQL Query: {memory.last_action.get('sql_query', 'N/A')[:200]}\n"
                    f"Parameters: {memory.last_action.get('parameters', 'N/A')}\n"
                )
            
            if memory_parts:
                memory_context = "\n".join(memory_parts)
        
        enriched = f"""
{memory_context if memory_context else ''}

DATABASE SCHEMA CONTEXT:
{context_text}

MANDATORY RULES TO FOLLOW:
{rules_text}

CURRENT USER REQUEST:
{prompt}
"""
        
        return enriched

    def _extract_ollama_text(self, resp):
        """Extract text from an Ollama HTTP response that may contain newline-delimited JSON chunks."""
        logger.debug(f"[_extract_ollama_text] Starting extraction | resp.status_code={resp.status_code}")
        
        # Try normal JSON parse first
        try:
            data = resp.json()
            logger.debug(f"[_extract_ollama_text] Parsed JSON successfully: type={type(data)} | keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            
            # If it's a single object, try common fields
            if isinstance(data, dict):
                for key in ('response', 'text', 'content'):
                    val = data.get(key)
                    if val:
                        logger.info(f"[_extract_ollama_text] ✓ Found '{key}' in dict: {str(val)[:100]}")
                        return val
                
                # handle choices array
                if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
                    ch = data['choices'][0]
                    if isinstance(ch, dict):
                        result = ch.get('text') or ch.get('message') or ch.get('content')
                        logger.info(f"[_extract_ollama_text] ✓ Found in choices[0]: {str(result)[:100]}")
                        return result
            
            # If it's a list, try to join known fields
            if isinstance(data, list):
                logger.debug(f"[_extract_ollama_text] Data is list with {len(data)} items")
                parts = []
                for idx, item in enumerate(data):
                    if isinstance(item, dict):
                        part = item.get('response') or item.get('text') or item.get('content') or ''
                        logger.debug(f"[_extract_ollama_text]   Item {idx}: extracted '{part[:50]}'")
                        parts.append(part)
                    else:
                        parts.append(str(item))
                result = ''.join(parts).strip()
                logger.info(f"[_extract_ollama_text] ✓ Joined list result (len={len(result)}): {result[:100]}")
                return result or None
        except Exception as e:
            logger.debug(f"[_extract_ollama_text] JSON parse failed: {str(e)}")

        # Fallback: parse newline-delimited JSON objects
        logger.debug(f"[_extract_ollama_text] Trying newline-delimited JSON fallback")
        text = resp.text or ''
        logger.debug(f"[_extract_ollama_text] resp.text length: {len(text)}")
        
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        logger.debug(f"[_extract_ollama_text] Found {len(lines)} non-empty lines")
        
        parts = []
        for line_idx, line in enumerate(lines):
            try:
                j = json.loads(line)
                extracted = j.get('response') or j.get('text') or j.get('content') or ''
                logger.debug(f"[_extract_ollama_text]   Line {line_idx}: JSON parsed, extracted '{extracted[:50]}'")
                parts.append(extracted)
            except Exception as parse_err:
                # Non-JSON content: include raw
                logger.debug(f"[_extract_ollama_text]   Line {line_idx}: Not JSON, including raw: {line[:50]}")
                parts.append(line)

        full = ''.join(parts).strip()
        logger.info(f"[_extract_ollama_text] ✓ Final result (len={len(full)}): {full[:100]}")
        return full or None
    
    def _parse_response(self, response_text):
        """Parse LLM response to extract structured data and validate SQL queries."""
        # Safety check for None response
        if not response_text:
            response_text = ("UNDERSTANDING: Unable to get a response from the LLM.\n"
                           "ACTION_TYPE: NONE\n"
                           "SQL_QUERY: N/A\n"
                           "PARAMETERS: N/A\n"
                           "CONFIDENCE: low\n"
                           "NEXT_STEP: Check LLM configuration and API keys.")
        
        parsed = {
            'explanation': response_text,
            'action': {},
            'action_type': None,
            'sql_query': None
        }
        
        try:
            # Extract understanding (labelled format)
            if 'UNDERSTANDING:' in response_text:
                try:
                    understanding = response_text.split('UNDERSTANDING:')[1].split('ACTION_TYPE:')[0].strip()
                    parsed['explanation'] = understanding
                except Exception:
                    # fallback to full text
                    parsed['explanation'] = response_text.strip()
            
            # Extract action type
            action_type = 'NONE'  # Initialize with default
            if 'ACTION_TYPE:' in response_text:
                action_type = response_text.split('ACTION_TYPE:')[1].split('\n')[0].strip()
                parsed['action_type'] = action_type
            else:
                # If no explicit action type, default to NONE
                parsed['action_type'] = 'NONE'
            
            # Normalize action type: convert to uppercase with underscores
            action_type_normalized = self._normalize_action_type(parsed['action_type'])
            parsed['action_type'] = action_type_normalized
            logger.debug(f"Normalized action type: '{parsed['action_type']}' (from '{action_type}')")
            
            # Extract SQL query (labelled) or detect raw SQL
            if 'SQL_QUERY:' in response_text:
                sql = response_text.split('SQL_QUERY:')[1].split('PARAMETERS:')[0].strip()
                if sql and sql.upper() != 'N/A':
                    parsed['sql_query'] = sql
            else:
                # rudimentary detection: if response looks like an SQL statement, capture it
                rt = response_text.strip()
                first_word = (rt.split()[0].upper() if rt else '')
                if first_word in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH'):
                    parsed['sql_query'] = rt
                    parsed['action_type'] = 'DATABASE_QUERY'
            
            # ═══════════════════════════════════════════════════════════════
            # DETERMINE QUERY MODE AND SET APPROPRIATE ACTION TYPE
            # ═══════════════════════════════════════════════════════════════
            if parsed['sql_query']:
                # Check database query mode
                self._load_active_database_mode()  # Refresh mode in case settings changed
                
                if self.active_db_query_mode == 'api':
                    # For API Query mode, query the local RAG database instead of direct SQL
                    parsed['action_type'] = 'RAG_QUERY'
                    logger.info(f"[MODE CHECK] Active database in API Query mode → Using RAG_QUERY")
                else:
                    # For Direct mode, use standard database query
                    parsed['action_type'] = 'DATABASE_QUERY'
                    logger.info(f"[MODE CHECK] Active database in Direct mode → Using DATABASE_QUERY")
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATE SQL QUERY AGAINST SCHEMA
            # ═══════════════════════════════════════════════════════════════
            if parsed['sql_query'] and parsed['action_type'] == 'DATABASE_QUERY':
                schema = self._extract_schema_from_rag()
                available_tables = schema.get('tables', [])
                
                if available_tables:
                    validation_result = self._validate_sql_against_schema(
                        parsed['sql_query'],
                        available_tables
                    )
                    
                    if not validation_result['valid']:
                        # Add validation warning to explanation
                        warning = f"\n\n⚠️  VALIDATION WARNING: {validation_result['message']}"
                        warning += f"\nAvailable tables: {', '.join(sorted(available_tables))}"
                        parsed['explanation'] += warning
                        
                        logger.warning(f"[SQL_VALIDATION] LLM suggested invalid SQL: {validation_result['message']}")
                    else:
                        logger.info(f"[SQL_VALIDATION] LLM SQL suggestion validated successfully")
            
            # Extract parameters
            if 'PARAMETERS:' in response_text:
                params = response_text.split('PARAMETERS:')[1].split('CONFIDENCE:')[0].strip()
                parsed['action']['parameters'] = params
            else:
                parsed['action']['parameters'] = parsed.get('sql_query') or 'N/A'
            
            # Extract confidence
            if 'CONFIDENCE:' in response_text:
                confidence = response_text.split('CONFIDENCE:')[1].split('\n')[0].strip()
                parsed['action']['confidence'] = confidence
            
            # Build action object with sane defaults
            parsed['action'] = {
                'type': parsed.get('action_type') or 'NONE',
                'sql_query': parsed.get('sql_query'),
                'parameters': parsed['action'].get('parameters'),
                'confidence': parsed['action'].get('confidence', 'medium')
            }
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
        
        return parsed
    
    def _normalize_action_type(self, action_type_raw):
        """Normalize action type string to standard format (e.g., 'Database Query' → 'DATABASE_QUERY')."""
        if not action_type_raw:
            return 'NONE'
        
        # Normalize: lowercase, strip, remove extra spaces FIRST
        normalized = action_type_raw.lower().strip()
        
        # Mapping of common variants to canonical form (all lowercase keys)
        mapping = {
            'database query': 'DATABASE_QUERY',
            'db query': 'DATABASE_QUERY',
            'sql': 'DATABASE_QUERY',
            'rag query': 'RAG_QUERY',
            'rag_query': 'RAG_QUERY',
            'local query': 'RAG_QUERY',
            'vector query': 'RAG_QUERY',
            'email': 'EMAIL',
            'email action': 'EMAIL',
            'send email': 'EMAIL',
            'read email': 'EMAIL',
            'url reading': 'URL_READING',
            'url read': 'URL_READING',
            'summarize url': 'URL_READING',
            'api call': 'API_CALL',
            'api': 'API_CALL',
            'scheduled activity': 'SCHEDULED_ACTIVITY',
            'schedule': 'SCHEDULED_ACTIVITY',
            'report': 'REPORT',
            'report generation': 'REPORT',
            'none': 'NONE',
        }
        
        # Check if normalized (lowercase) matches a known mapping
        if normalized in mapping:
            result = mapping[normalized]
            logger.debug(f"_normalize_action_type: '{action_type_raw}' → '{result}'")
            return result
        
        # Fallback: convert to UPPERCASE_WITH_UNDERSCORES
        result = normalized.upper().replace(' ', '_')
        logger.debug(f"_normalize_action_type: '{action_type_raw}' → '{result}' (fallback)")
        return result
    
    def continue_conversation(self, conversation_id, user_message):
        """Continue an ongoing conversation for clarification."""
        try:
            # Refresh active model in case settings changed while server is running
            try:
                self._ensure_active_model()
            except Exception:
                logger.debug("_ensure_active_model failed during continue_conversation")
            # Use Session.get to avoid SQLAlchemy 2.0 deprecation warning
            conversation = db.session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError("Conversation not found")
            
            # Use chat history for context
            history = [m.to_dict() for m in conversation.messages]
            
            # Build chat context
            chat_context = "\n".join([
                f"{m['role']}: {m['content']}" 
                for m in history[-5:]  # Last 5 messages
            ])
            
            # Generate response
            prompt = f"Previous conversation:\n{chat_context}\n\nUser: {user_message}"
            
            if not self.model:
                resp_text = "The LLM is not available. Please configure an LLM (Gemini or Claude) with a valid API key."
            elif self.model_type == 'claude' and self.claude_client:
                # Use Claude API
                try:
                    message = self.claude_client.messages.create(
                        model=self.claude_model_id,
                        max_tokens=1024,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    resp_text = message.content[0].text
                except Exception as e:
                    logger.error(f"Claude API error: {str(e)}")
                    resp_text = f"Error calling Claude API: {str(e)}"
            elif self.model_type == 'ollama' and self.ollama_available:
                # Call local Ollama for continuation
                try:
                    resp_text = None
                    if requests and self.ollama_host and self.ollama_model:
                        post_endpoints = ['/api/generate', '/api/completions', '/chat', '/api/chat']
                        for ep in post_endpoints:
                            try:
                                url = f"{self.ollama_host.rstrip('/')}{ep}"
                                payloads = [
                                    {'model': self.ollama_model, 'prompt': prompt, 'max_tokens': 1024},
                                    {'model': self.ollama_model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 1024},
                                ]
                                # Normalize model id for continuation requests as well
                                normalized_model = self.ollama_model
                                try:
                                    if isinstance(normalized_model, str) and normalized_model.lower().startswith('ollama:'):
                                        normalized_model = normalized_model.split(':', 1)[1]
                                except Exception:
                                    pass

                                payloads = [
                                    {'model': normalized_model or self.ollama_model, 'prompt': prompt, 'max_tokens': 1024},
                                    {'model': normalized_model or self.ollama_model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 1024},
                                ]
                                for payload in payloads:
                                    try:
                                        logger.debug(f"Calling Ollama continuation endpoint {url} with payload keys: {list(payload.keys())}")
                                        resp = requests.post(url, json=payload, timeout=10)
                                    except Exception:
                                        resp = None
                                    if not resp:
                                        continue
                                    if resp.status_code == 200:
                                        try:
                                            data = resp.json()
                                            if isinstance(data, dict):
                                                if 'text' in data:
                                                    resp_text = data.get('text')
                                                elif 'content' in data:
                                                    resp_text = data.get('content')
                                                elif 'choices' in data and isinstance(data['choices'], list) and data['choices']:
                                                    ch = data['choices'][0]
                                                    if isinstance(ch, dict):
                                                        resp_text = ch.get('text') or ch.get('message') or ch.get('content')
                                            if resp_text:
                                                break
                                        except Exception:
                                            try:
                                                resp_text = resp.text
                                                break
                                            except Exception:
                                                continue
                            except Exception:
                                continue
                        if not resp_text:
                            resp_text = "(No response from local Ollama)"
                except Exception as e:
                    logger.debug(f"Error calling Ollama for continuation: {str(e)}")
            else:
                # Use Gemini API
                response = self.model.generate_content(prompt)
                resp_text = response.text
            
            # Store messages
            user_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role='user',
                content=user_message
            )
            db.session.add(user_msg)
            
            assistant_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role='assistant',
                content=resp_text or ''
            )
            db.session.add(assistant_msg)
            db.session.commit()
            
            return {
                'conversation_id': conversation_id,
                'response': resp_text,
                'message_id': assistant_msg.id
            }
        
        except Exception as e:
            logger.error(f"Error continuing conversation: {str(e)}")
            raise

    def call_llm_with_retries(prompt, client, max_retries=3, backoff_seconds=1):
        """
        Call the LLM, retry on transient failures, and log raw response for debugging.
        Returns text on success or raises/returns a clear error on failure.
        """
        for attempt in range(1, max_retries + 1):
            try:
                # Example: raw_resp = client.generate(prompt=prompt)  # adapt to your client API
                raw_resp = client.generate(prompt=prompt)  # ...existing code...
                # Log the raw response object (helps debug when parsed text is empty)
                logger.info("LLM raw response (attempt %d): %s", attempt, repr(raw_resp))

                # Extract text depending on client structure
                response_text = None
                if isinstance(raw_resp, dict):
                    # adjust keys to match your client
                    response_text = raw_resp.get("text") or raw_resp.get("output") or ""
                else:
                    # try common attributes
                    response_text = getattr(raw_resp, "text", None) or getattr(raw_resp, "output_text", None) or ""

                # Final sanity check
                if not response_text or not str(response_text).strip():
                    raise ValueError("Empty response_text from LLM")

                logger.info("Parsed response_text (length=%d)", len(response_text))
                return response_text

            except Exception as exc:
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt, max_retries, exc)
                if attempt == max_retries:
                    logger.error("Unable to get a response from the LLM after %d attempts: %s", max_retries, exc)
                    # Return a clear diagnostic message instead of None
                    return "Unable to get a response from the LLM: {}".format(exc)
                time.sleep(backoff_seconds * attempt)