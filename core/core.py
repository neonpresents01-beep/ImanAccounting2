# core/app_core.py
# ============================================================
# هسته مرکزی برنامه (AppCore) — نسخه 2.0
# EventBus + Theme + AI + Agent + Context + Services
# ============================================================

from PyQt5.QtCore import QObject, pyqtSignal
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from collections import deque
import logging
import threading
import pickle
import os
import json
import re

logger = logging.getLogger(__name__)


# ============================================================
# EventType — انواع eventهای سراسری
# ============================================================

class EventType:
    """انواع eventهای سراسری برنامه"""
    
    # تم
    THEME_CHANGED = "theme.changed"
    THEME_TOGGLED = "theme.toggled"
    
    # AI
    AI_QUERY_STARTED = "ai.query.started"
    AI_QUERY_FINISHED = "ai.query.finished"
    AI_QUERY_ERROR = "ai.query.error"
    AI_MODEL_LOADED = "ai.model.loaded"
    AI_MEMORY_UPDATED = "ai.memory.updated"
    AI_STATUS_CHANGED = "ai.status.changed"
    
    # Agent
    AGENT_ACTION_STARTED = "agent.action.started"
    AGENT_ACTION_FINISHED = "agent.action.finished"
    AGENT_ACTION_FAILED = "agent.action.failed"
    AGENT_LEARNED = "agent.learned"
    
    # داده
    DATA_CHANGED = "data.changed"
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_REFRESH = "data.refresh"
    
    # کاربر
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LEVEL_CHANGED = "user.level_changed"
    PERMISSION_DENIED = "permission.denied"
    
    # ماژول
    MODULE_LOADED = "module.loaded"
    MODULE_UNLOADED = "module.unloaded"
    MODULE_ACTIVATED = "module.activated"
    PAGE_CHANGED = "page.changed"
    
    # پلاگین
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UNINSTALLED = "plugin.uninstalled"
    PLUGIN_ACTIVATED = "plugin.activated"
    
    # اطلاع‌رسانی
    NOTIFICATION = "notification"
    NOTIFY_SUCCESS = "notification.success"
    NOTIFY_WARNING = "notification.warning"
    NOTIFY_ERROR = "notification.error"
    NOTIFY_INFO = "notification.info"
    
    # برنامه
    APP_STARTED = "app.started"
    APP_CLOSING = "app.closing"
    APP_BUSY = "app.busy"
    APP_IDLE = "app.idle"
    APP_READY = "app.ready"
    
    # عمومی
    GLOBAL = "global"


# ============================================================
# EventBus — سیستم پیام‌رسانی مرکزی
# ============================================================

class EventBus(QObject):
    """سیستم پیام‌رسانی مرکزی — مثل یه سرور داخلی"""
    
    # ===== تم =====
    theme_changed = pyqtSignal(str)
    theme_toggled = pyqtSignal(str)
    
    # ===== AI =====
    ai_query_started = pyqtSignal(str)
    ai_query_finished = pyqtSignal(str, str)
    ai_query_error = pyqtSignal(str, str)
    ai_model_loaded = pyqtSignal(str)
    ai_memory_updated = pyqtSignal(dict)
    ai_status_changed = pyqtSignal(str, bool)
    
    # ===== Agent =====
    agent_action_started = pyqtSignal(str, dict)
    agent_action_finished = pyqtSignal(str, dict)
    agent_action_failed = pyqtSignal(str, str)
    agent_learned = pyqtSignal(str, str)
    
    # ===== داده =====
    data_changed = pyqtSignal(str, str, dict)
    data_refresh = pyqtSignal(str)
    
    # ===== کاربر =====
    user_login = pyqtSignal(dict)
    user_logout = pyqtSignal()
    user_level_changed = pyqtSignal(str)
    permission_denied = pyqtSignal(str, str)
    
    # ===== ماژول =====
    module_loaded = pyqtSignal(str)
    module_unloaded = pyqtSignal(str)
    module_activated = pyqtSignal(str)
    page_changed = pyqtSignal(str)
    
    # ===== پلاگین =====
    plugin_installed = pyqtSignal(str)
    plugin_uninstalled = pyqtSignal(str)
    plugin_activated = pyqtSignal(str)
    
    # ===== اطلاع‌رسانی =====
    notification = pyqtSignal(str, str)
    notify_success = pyqtSignal(str)
    notify_warning = pyqtSignal(str)
    notify_error = pyqtSignal(str)
    notify_info = pyqtSignal(str)
    
    # ===== برنامه =====
    app_started = pyqtSignal()
    app_closing = pyqtSignal()
    app_busy = pyqtSignal(str)
    app_idle = pyqtSignal()
    app_ready = pyqtSignal()
    
    # ===== عمومی =====
    global_event = pyqtSignal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._history: List[Dict] = []
        self._max_history = 200
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        
        self._connect_signals_to_log()
        logger.info("📡 EventBus راه‌اندازی شد")
    
    def _connect_signals_to_log(self):
        signal_names = [
            'theme_changed', 'theme_toggled',
            'ai_query_started', 'ai_query_finished', 'ai_query_error',
            'ai_model_loaded', 'ai_memory_updated', 'ai_status_changed',
            'agent_action_started', 'agent_action_finished',
            'agent_action_failed', 'agent_learned',
            'data_changed', 'data_refresh',
            'user_login', 'user_logout', 'user_level_changed', 'permission_denied',
            'module_loaded', 'module_unloaded', 'module_activated', 'page_changed',
            'plugin_installed', 'plugin_uninstalled', 'plugin_activated',
            'notification', 'notify_success', 'notify_warning', 'notify_error', 'notify_info',
            'app_started', 'app_closing', 'app_busy', 'app_idle', 'app_ready',
        ]
        
        for name in signal_names:
            try:
                getattr(self, name).connect(
                    lambda *args, n=name: self._log(n, args)
                )
            except Exception as e:
                logger.warning(f"خطا در اتصال {name}: {e}")
    
    def _log(self, name: str, args: tuple):
        try:
            with self._lock:
                self._history.append({
                    'name': name,
                    'args': [str(a)[:200] for a in args],
                    'timestamp': datetime.now().isoformat()
                })
                if len(self._history) > self._max_history:
                    self._history.pop(0)
        except Exception:
            pass
    
    def publish(self, event_name: str, payload: dict = None):
        try:
            self.global_event.emit(event_name, payload or {})
        except Exception as e:
            logger.error(f"خطا در publish {event_name}: {e}")
    
    def subscribe(self, event_name: str, callback: Callable):
        try:
            with self._lock:
                self._subscribers.setdefault(event_name, []).append(callback)
        except Exception as e:
            logger.error(f"خطا در subscribe: {e}")
    
    def unsubscribe(self, event_name: str, callback: Callable):
        try:
            with self._lock:
                if event_name in self._subscribers:
                    self._subscribers[event_name] = [
                        c for c in self._subscribers[event_name] if c != callback
                    ]
        except Exception as e:
            logger.error(f"خطا در unsubscribe: {e}")
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            return list(self._history[-limit:])
    
    def clear_history(self):
        with self._lock:
            self._history.clear()
    
    def get_stats(self) -> Dict:
        with self._lock:
            return {
                'total_events': len(self._history),
                'subscribers': {k: len(v) for k, v in self._subscribers.items()}
            }


# ============================================================
# ContextProvider
# ============================================================

class ContextProvider:
    """یه provider داده از یه ویجت"""
    
    def __init__(self, name, provider, priority=0, description="", widget=None):
        self.name = name
        self.provider = provider
        self.priority = priority
        self.description = description
        self._widget = widget
    
    def get_data(self) -> dict:
        try:
            data = self.provider()
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning(f"خطا در context '{self.name}': {e}")
            return {'error': str(e)}
    
    def is_widget_alive(self) -> bool:
        if self._widget is None:
            return True
        return self._widget is not None


# ============================================================
# ContextRegistry
# ============================================================

class ContextRegistry(QObject):
    """رجیستری داده‌های context"""
    
    provider_registered = pyqtSignal(str)
    provider_unregistered = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._providers: Dict[str, ContextProvider] = {}
        self._lock = threading.RLock()
        logger.info("📋 ContextRegistry راه‌اندازی شد")
    
    def register(self, name, provider, priority=0, description="", widget=None):
        try:
            with self._lock:
                self._providers[name] = ContextProvider(
                    name, provider, priority, description, widget
                )
            self.provider_registered.emit(name)
            logger.info(f"✅ Context registered: {name}")
        except Exception as e:
            logger.error(f"خطا در register '{name}': {e}")
    
    def unregister(self, name: str):
        try:
            with self._lock:
                if name in self._providers:
                    del self._providers[name]
            self.provider_unregistered.emit(name)
        except Exception as e:
            logger.error(f"خطا در unregister '{name}': {e}")
    
    def get(self, name: str) -> dict:
        with self._lock:
            provider = self._providers.get(name)
        return provider.get_data() if provider else {}
    
    def get_all(self, max_priority: int = None) -> Dict[str, dict]:
        result = {}
        with self._lock:
            providers = list(self._providers.values())
        providers.sort(key=lambda p: p.priority, reverse=True)
        for provider in providers:
            if max_priority is not None and provider.priority < max_priority:
                continue
            data = provider.get_data()
            if data and 'error' not in data:
                result[provider.name] = data
        return result
    
    def list_providers(self) -> List[str]:
        with self._lock:
            return list(self._providers.keys())
    
    def get_stats(self) -> dict:
        with self._lock:
            return {
                'count': len(self._providers),
                'providers': {
                    name: {
                        'priority': p.priority,
                        'description': p.description,
                    }
                    for name, p in self._providers.items()
                }
            }


# ============================================================
# ConversationMemory
# ============================================================

class ConversationMemory:
    """حافظه مکالمات"""
    
    def __init__(self, max_size=500):
        self.max_size = max_size
        self.conversations = deque(maxlen=max_size)
        self.intent_patterns = {
            'balance_cash': ['موجودی صندوق'],
            'balance_bank': ['موجودی بانک'],
            'profit': ['سود این ماه'],
            'sales': ['فروش ماه'],
            'help': ['راهنما'],
        }
        self.word_vectors = {}
        self._load()
    
    def _get_path(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "conversation_memory.pkl"
        )
    
    def _load(self):
        path = self._get_path()
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                if data:
                    self.conversations = deque(
                        data.get('conversations', []), maxlen=self.max_size
                    )
                    self.intent_patterns = data.get('intent_patterns', self.intent_patterns)
                    self.word_vectors = data.get('word_vectors', {})
            except Exception as e:
                logger.warning(f"خطا در بارگذاری حافظه: {e}")
    
    def save(self):
        try:
            with open(self._get_path(), 'wb') as f:
                pickle.dump({
                    'conversations': list(self.conversations),
                    'intent_patterns': self.intent_patterns,
                    'word_vectors': self.word_vectors
                }, f)
        except Exception as e:
            logger.warning(f"خطا در ذخیره حافظه: {e}")
    
    def add_conversation(self, query, response, intent=None, was_helpful=True):
        try:
            intent = intent or self.detect_intent(query)
            self.conversations.append({
                'query': query,
                'response': response,
                'intent': intent,
                'timestamp': datetime.now().isoformat(),
                'was_helpful': was_helpful
            })
            for word in query.split():
                if len(word) > 2:
                    self.word_vectors.setdefault(word, {'intent': intent, 'count': 0})
                    self.word_vectors[word]['count'] += 1
            if len(self.conversations) % 50 == 0:
                self.save()
        except Exception as e:
            logger.warning(f"خطا در add_conversation: {e}")
    
    def detect_intent(self, query):
        q_lower = query.lower()
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern.lower() in q_lower:
                    return intent
        return 'unknown'
    
    def get_stats(self):
        total = len(self.conversations)
        helpful = sum(1 for c in self.conversations if c.get('was_helpful', True))
        return {
            'total': total,
            'helpful_rate': (helpful / total * 100) if total > 0 else 0,
            'vocab_size': len(self.word_vectors)
        }
    
    def search_similar(self, query, limit=5):
        q_words = set(query.split())
        results = []
        for conv in self.conversations:
            c_words = set(conv['query'].split())
            sim = len(q_words & c_words) / max(len(q_words), len(c_words), 1)
            if sim > 0.3:
                results.append({
                    'query': conv['query'],
                    'response': conv['response'],
                    'similarity': sim,
                    'intent': conv['intent']
                })
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
    
    def clear(self):
        self.conversations.clear()
        self.word_vectors.clear()


# ============================================================
# ThemeService
# ============================================================

class ThemeService(QObject):
    """سرویس مدیریت تم"""
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._manager = None
        self._current_theme_name = "light"
        self._is_dark = False
    
    def attach_manager(self, theme_manager):
        self._manager = theme_manager
        self._current_theme_name = theme_manager.get_theme_name()
        self._is_dark = (self._current_theme_name == "dark")
        logger.info(f"✅ ThemeService متصل شد: {self._current_theme_name}")
    
    def set_theme(self, name: str):
        if not self._manager:
            return
        try:
            self._current_theme_name = name
            self._is_dark = (name == "dark")
            if self._manager.get_theme_name() != name:
                self._manager.set_theme(name)
            self.event_bus.theme_changed.emit(name)
            self.event_bus.publish(
                EventType.THEME_CHANGED,
                {'theme': name, 'is_dark': self._is_dark}
            )
        except Exception as e:
            logger.error(f"خطا در تغییر تم: {e}")
    
    def _on_manager_theme_changed(self, theme_name: str):
        self._current_theme_name = theme_name
        self._is_dark = (theme_name == "dark")
        self.event_bus.theme_changed.emit(theme_name)
        self.event_bus.publish(
            EventType.THEME_CHANGED,
            {'theme': theme_name, 'is_dark': self._is_dark}
        )
    
    def toggle_theme(self):
        new_theme = "light" if self._is_dark else "dark"
        self.set_theme(new_theme)
        self.event_bus.theme_toggled.emit(new_theme)
    
    def is_dark(self) -> bool:
        return self._is_dark
    
    def get_current(self) -> str:
        return self._current_theme_name
    
    def get_stylesheet(self) -> str:
        if self._manager:
            return self._manager.get_stylesheet()
        return ""


# ============================================================
# LearningMemory — حافظه یادگیری Agent
# ============================================================

class LearningMemory:
    """حافظه یادگیری AI Agent"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.query_to_action: Dict[str, str] = {}
        self.action_stats: Dict[str, Dict] = {}
        self.history: List[Dict] = []
        self._file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ai_learning.pkl"
        )
        self._load()
    
    def _load(self):
        try:
            if os.path.exists(self._file_path):
                with open(self._file_path, 'rb') as f:
                    data = pickle.load(f)
                    self.query_to_action = data.get('query_to_action', {})
                    self.action_stats = data.get('action_stats', {})
                    self.history = data.get('history', [])
                logger.info(f"✅ حافظه یادگیری: {len(self.query_to_action)} الگو")
        except Exception as e:
            logger.warning(f"خطا در بارگذاری حافظه: {e}")
    
    def save(self):
        try:
            with open(self._file_path, 'wb') as f:
                pickle.dump({
                    'query_to_action': self.query_to_action,
                    'action_stats': self.action_stats,
                    'history': self.history[-self.max_size:],
                }, f)
        except Exception as e:
            logger.warning(f"خطا در ذخیره حافظه: {e}")
    
    def remember(self, query, action_name, success, parameters=None):
        try:
            q_key = self._normalize(query)
            
            if success:
                existing = self.query_to_action.get(q_key, {})
                self.query_to_action[q_key] = {
                    'action': action_name,
                    'parameters': parameters or {},
                    'count': existing.get('count', 0) + 1,
                    'last_used': datetime.now().isoformat(),
                }
            
            if action_name not in self.action_stats:
                self.action_stats[action_name] = {'total': 0, 'success': 0, 'failed': 0}
            
            self.action_stats[action_name]['total'] += 1
            if success:
                self.action_stats[action_name]['success'] += 1
            else:
                self.action_stats[action_name]['failed'] += 1
            
            self.history.append({
                'query': query,
                'action': action_name,
                'success': success,
                'parameters': parameters or {},
                'timestamp': datetime.now().isoformat(),
            })
            
            if len(self.history) > self.max_size:
                self.history = self.history[-self.max_size:]
            
            if len(self.history) % 10 == 0:
                self.save()
        except Exception as e:
            logger.warning(f"خطا در remember: {e}")
    
    def _normalize(self, query: str) -> str:
        q = query.lower().strip()
        q = re.sub(r'\s+', ' ', q)
        q = re.sub(r'[؟?!.,]', '', q)
        return q
    
    def recall(self, query: str) -> Optional[dict]:
        try:
            q_key = self._normalize(query)
            
            if q_key in self.query_to_action:
                return self.query_to_action[q_key]
            
            q_words = set(q_key.split())
            for saved_query, action_info in self.query_to_action.items():
                s_words = set(saved_query.split())
                if not q_words or not s_words:
                    continue
                sim = len(q_words & s_words) / max(len(q_words), len(s_words))
                if sim > 0.75:
                    return action_info
            
            return None
        except Exception as e:
            logger.warning(f"خطا در recall: {e}")
            return None
    
    def get_stats(self) -> dict:
        return {
            'learned_patterns': len(self.query_to_action),
            'total_actions': len(self.history),
            'action_stats': self.action_stats,
        }
    
    def clear(self):
        self.query_to_action.clear()
        self.action_stats.clear()
        self.history.clear()
        self.save()


# ============================================================
# Action & ActionType
# ============================================================

class ActionType:
    NAVIGATE = "navigate"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    REPORT = "report"
    SEARCH = "search"
    EXPORT = "export"
    CALCULATE = "calculate"
    CUSTOM = "custom"


class Action:
    """یه اکشن قابل اجرا توسط Agent"""
    
    def __init__(
        self,
        name: str,
        action_type: str,
        handler: Callable,
        description: str = "",
        keywords: List[str] = None,
        requires_confirmation: bool = False,
    ):
        self.name = name
        self.action_type = action_type
        self.handler = handler
        self.description = description
        self.keywords = keywords or []
        self.requires_confirmation = requires_confirmation
    
    def matches(self, query: str) -> float:
        q = query.lower().strip()
        if not self.keywords:
            return 0.0
        matches = 0
        for kw in self.keywords:
            if kw.lower() in q:
                matches += 1
        return min(matches / len(self.keywords) * 1.2, 1.0)
    
    def execute(self, **params) -> dict:
        try:
            result = self.handler(**params)
            return {'success': True, 'result': result, 'action': self.name}
        except Exception as e:
            logger.error(f"خطا در {self.name}: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'action': self.name}
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'type': self.action_type,
            'description': self.description,
            'keywords': self.keywords,
        }


# ============================================================
# AIAgent
# ============================================================

class AIAgent(QObject):
    """AI Agent خودکفا با یادگیری"""
    
    def __init__(self, event_bus, context_registry, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self.context_registry = context_registry
        self.actions: Dict[str, Action] = {}
        self.memory = LearningMemory()
        self._enabled = True
        logger.info("🤖 AI Agent راه‌اندازی شد")
    
    def register_action(self, action: Action):
        self.actions[action.name] = action
        logger.info(f"✅ Action: {action.name}")
    
    def register_simple(
        self,
        name: str,
        action_type: str,
        handler: Callable,
        keywords: List[str],
        description: str = "",
        requires_confirmation: bool = False,
    ):
        action = Action(
            name=name,
            action_type=action_type,
            handler=handler,
            description=description,
            keywords=keywords,
            requires_confirmation=requires_confirmation,
        )
        self.register_action(action)
    
    def unregister_action(self, name: str):
        if name in self.actions:
            del self.actions[name]
    
    def list_actions(self) -> List[dict]:
        return [a.to_dict() for a in self.actions.values()]
    
    def execute(self, query: str, auto_learn: bool = True) -> dict:
        if not self._enabled:
            return {'success': False, 'message': 'Agent غیرفعال', 'source': 'disabled'}
        
        try:
            recalled = self.memory.recall(query)
            if recalled:
                action_name = recalled.get('action')
                action = self.actions.get(action_name)
                
                if action:
                    logger.info(f"🧠 از حافظه: {action_name}")
                    result = self._execute_action(action, query, recalled.get('parameters', {}))
                    result['source'] = 'memory'
                    return result
            
            best = self._find_best_action(query)
            
            if not best:
                return {
                    'success': False,
                    'message': 'متوجه نشدم چه کاری می‌خوای',
                    'source': 'none',
                    'suggestions': self._suggest_actions(query),
                }
            
            result = self._execute_action(best, query)
            result['source'] = 'analysis'
            
            if auto_learn and result['success']:
                self.memory.remember(query, best.name, True)
                self.event_bus.agent_learned.emit(query, best.name)
            
            return result
        
        except Exception as e:
            logger.error(f"خطا در execute: {e}", exc_info=True)
            return {'success': False, 'message': f'خطا: {str(e)}', 'source': 'error'}
    
    def _find_best_action(self, query: str) -> Optional[Action]:
        scores = [(a.matches(query), a) for a in self.actions.values()]
        scores = [s for s in scores if s[0] > 0]
        
        if not scores:
            return None
        
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1] if scores[0][0] >= 0.3 else None
    
    def _suggest_actions(self, query: str) -> List[dict]:
        scores = [(a.matches(query), a) for a in self.actions.values()]
        scores = [s for s in scores if s[0] > 0]
        scores.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {'name': a.name, 'description': a.description, 'keywords': a.keywords}
            for _, a in scores[:5]
        ]
    
    def _execute_action(self, action: Action, query: str, parameters: dict = None) -> dict:
        try:
            logger.info(f"⚡ اجرای: {action.name}")
            self.event_bus.agent_action_started.emit(action.name, parameters or {})
            
            result = action.execute(**(parameters or {}))
            
            if result['success']:
                self.event_bus.agent_action_finished.emit(action.name, result)
                return {
                    'success': True,
                    'action': action.name,
                    'result': result.get('result'),
                    'message': f'✅ {action.description or action.name}',
                }
            else:
                self.event_bus.agent_action_failed.emit(action.name, result.get('error', ''))
                return {
                    'success': False,
                    'action': action.name,
                    'message': f"❌ {result.get('error')}",
                }
        except Exception as e:
            logger.error(f"خطا در اجرا: {e}")
            return {'success': False, 'action': action.name, 'message': f"❌ {str(e)}"}
    
    def get_full_context(self) -> dict:
        return self.context_registry.get_all()
    
    def get_stats(self) -> dict:
        return {
            'actions_count': len(self.actions),
            'learning': self.memory.get_stats(),
            'enabled': self._enabled,
        }
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def clear_learning(self):
        self.memory.clear()


# ============================================================
# AIService
# ============================================================

class AIService(QObject):
    """سرویس هوش مصنوعی با Agent"""
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        
        self.context_registry = ContextRegistry(self)
        self.agent = AIAgent(event_bus, self.context_registry, self)
        
        self._api_manager = None
        self._memory = ConversationMemory()
        self._speech = None
        
        self._is_connected = False
        self._is_available = False
        self._gpu_available = False
        self._speech_available = False
        self._version = "0.0.0"
        
        self._init_status()
        logger.info(f"🧠 AIService راه‌اندازی شد")
    
    def _init_status(self):
        try:
            import ImanAILite as imanai
            self._is_available = True
            try:
                self._gpu_available = imanai.is_gpu_available()
            except Exception:
                self._gpu_available = False
            self._version = getattr(imanai, '__version__', '4.0.0')
        except ImportError:
            self._is_available = False
            self._version = "N/A"
        
        try:
            from ImanAILite.speech import ImanSpeech
            self._speech_available = True
        except ImportError:
            self._speech_available = False
    
    def attach_api_manager(self, api_manager):
        self._api_manager = api_manager
        self._is_connected = api_manager.is_connected if api_manager else False
        logger.info(f"🌐 AIService: API {'متصل' if self._is_connected else 'آفلاین'}")
    
    def attach_memory(self, memory):
        self._memory = memory
    
    def attach_speech(self, speech):
        self._speech = speech
    
    # ============================================================
    # Context API
    # ============================================================
    
    def register_context(self, name, provider, priority=0, description="", widget=None):
        self.context_registry.register(name, provider, priority, description, widget)
    
    def unregister_context(self, name: str):
        self.context_registry.unregister(name)
    
    def get_context(self, name: str = None) -> dict:
        if name:
            return self.context_registry.get(name)
        return self.context_registry.get_all()
    
    # ============================================================
    # Action API
    # ============================================================
    
    def register_action(self, name, action_type, handler, keywords, description=""):
        self.agent.register_simple(
            name=name, action_type=action_type, handler=handler,
            keywords=keywords, description=description,
        )
    
    def execute(self, query: str) -> dict:
        return self.agent.execute(query)
    
    def get_agent_stats(self) -> dict:
        return self.agent.get_stats()
    
    # ============================================================
    # Query
    # ============================================================
    
    def ask(self, query: str, use_context: bool = True, context_filter: List[str] = None) -> Optional[str]:
        try:
            self.event_bus.ai_query_started.emit(query)
            prompt = self._build_prompt(query, use_context, context_filter)
            
            if self._is_connected and self._api_manager:
                try:
                    response = self._api_manager.generate_response(prompt)
                    if response and len(response) > 10:
                        self.event_bus.ai_query_finished.emit(query, response)
                        return response
                except Exception as e:
                    logger.warning(f"خطا در API: {e}")
            
            response = self._fallback_response(query)
            self.event_bus.ai_query_finished.emit(query, response)
            return response
        except Exception as e:
            logger.error(f"خطا در ask: {e}")
            self.event_bus.ai_query_error.emit(query, str(e))
            return None
    
    def _build_prompt(self, query, use_context, context_filter=None):
        if not use_context:
            return query
        
        context = self.get_context()
        
        if context_filter:
            context = {k: v for k, v in context.items() if k in context_filter}
        
        if not context:
            return query
        
        context_text = self._format_context(context)
        return f"""تو دستیار حسابداری ImanAI هستی.

داده‌های لحظه‌ای:
{context_text}

سوال: {query}

پاسخ کوتاه و دقیق بده."""
    
    def _format_context(self, context: dict) -> str:
        lines = []
        for name, data in context.items():
            if not data:
                continue
            lines.append(f"\n[{name}]")
            for k, v in data.items():
                if isinstance(v, (int, float)):
                    lines.append(f"  • {k}: {v:,}" if isinstance(v, (int, float)) and v > 1000 else f"  • {k}: {v}")
                else:
                    lines.append(f"  • {k}: {str(v)[:100]}")
        return "\n".join(lines) if lines else "(داده‌ای نیست)"
    
    def _fallback_response(self, query: str) -> str:
        q = query.lower()
        
        ctx = self.get_context('accounting')
        if "موجودی" in q and ctx:
            if "صندوق" in q and 'cash' in ctx:
                return f"💰 موجودی صندوق: {ctx['cash']:,.0f} ریال"
            if "بانک" in q and 'bank' in ctx:
                return f"🏦 موجودی بانک: {ctx['bank']:,.0f} ریال"
        
        if "مشتری" in q:
            ctx = self.get_context('customers')
            if ctx:
                return f"👥 مشتریان: {ctx.get('total', 0)} نفر"
        
        if "کالا" in q or "انبار" in q:
            ctx = self.get_context('inventory')
            if ctx:
                return f"📦 کالاها: {ctx.get('total_products', 0)} قلم"
        
        if "راهنما" in q:
            return self._get_help_response()
        
        if any(w in q for w in ["سلام", "خوبی"]):
            return "👋 سلام! چطور می‌تونم کمکت کنم؟"
        
        if "موجودی" in q:
            try:
                from database import AccountingHelper
                if "صندوق" in q:
                    return f"💰 موجودی صندوق: {AccountingHelper.get_account_balance('1101'):,.0f} ریال"
                if "بانک" in q:
                    return f"🏦 موجودی بانک: {AccountingHelper.get_account_balance('1102'):,.0f} ریال"
            except Exception:
                pass
        
        return "🤔 متوجه نشدم. برای راهنما بپرس 'راهنما'."
    
    def _get_help_response(self) -> str:
        providers = self.context_registry.list_providers()
        ctx_info = f"\n📋 متصل: {', '.join(providers)}" if providers else ""
        
        return f"""
📚 **راهنمای ImanAI**

💰 مالی، 👥 مشتریان، 📦 کالاها، 📄 اسناد
🧠 پیشنهاد حساب، 🎤 صوتی، 🤖 Agent خودکار
{ctx_info}

💡 **هرچه بیشتر استفاده کنی، باهوش‌تر می‌شم!**
"""
    
    def save_conversation(self, query, response, intent=None):
        if self._memory:
            try:
                self._memory.add_conversation(query, response, intent)
                self.event_bus.ai_memory_updated.emit({'query': query, 'intent': intent})
            except Exception as e:
                logger.warning(f"خطا در ذخیره حافظه: {e}")
    
    def get_memory_stats(self) -> dict:
        if self._memory:
            try:
                return self._memory.get_stats()
            except Exception:
                pass
        return {'total': 0, 'helpful_rate': 0, 'vocab_size': 0}
    
    def get_status(self) -> dict:
        return {
            'available': self._is_available,
            'connected': self._is_connected,
            'gpu': self._gpu_available,
            'speech': self._speech_available,
            'version': self._version,
        }
    
    def update_connection_status(self, is_connected: bool):
        self._is_connected = is_connected
        self.event_bus.ai_status_changed.emit('api', is_connected)


# ============================================================
# NotificationService
# ============================================================

class NotificationService(QObject):
    """سرویس اطلاع‌رسانی"""
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._history: List[Dict] = []
    
    def _notify(self, level: str, message: str):
        try:
            self._history.append({
                'level': level, 'message': message,
                'timestamp': datetime.now().isoformat()
            })
            self.event_bus.notification.emit(level, message)
            if level == 'success':
                self.event_bus.notify_success.emit(message)
            elif level == 'warning':
                self.event_bus.notify_warning.emit(message)
            elif level == 'error':
                self.event_bus.notify_error.emit(message)
            else:
                self.event_bus.notify_info.emit(message)
        except Exception as e:
            logger.error(f"خطا در notify: {e}")
    
    def success(self, message: str): self._notify('success', message)
    def warning(self, message: str): self._notify('warning', message)
    def error(self, message: str): self._notify('error', message)
    def info(self, message: str): self._notify('info', message)


# ============================================================
# DataService
# ============================================================

class DataService(QObject):
    """سرویس داده"""
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
    
    def notify_change(self, entity: str, action: str, data: dict = None):
        self.event_bus.data_changed.emit(entity, action, data or {})
        self.event_bus.publish(
            EventType.DATA_CHANGED,
            {'entity': entity, 'action': action, 'data': data or {}}
        )
    
    def created(self, entity: str, data: dict = None):
        self.notify_change(entity, 'create', data)
    
    def updated(self, entity: str, data: dict = None):
        self.notify_change(entity, 'update', data)
    
    def deleted(self, entity: str, data: dict = None):
        self.notify_change(entity, 'delete', data)
    
    def refresh(self, entity: str):
        self.event_bus.data_refresh.emit(entity)


# ============================================================
# UserService
# ============================================================

class UserService(QObject):
    """سرویس کاربر"""
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._current_user: Optional[dict] = None
    
    def login(self, user_info: dict):
        self._current_user = user_info
        self.event_bus.user_login.emit(user_info)
        logger.info(f"👤 {user_info.get('username')} وارد شد")
    
    def logout(self):
        self._current_user = None
        self.event_bus.user_logout.emit()
    
    def change_level(self, new_level: str):
        if self._current_user:
            self._current_user['level'] = new_level
            self.event_bus.user_level_changed.emit(new_level)
    
    def get_current(self) -> Optional[dict]:
        return self._current_user
    
    def has_permission(self, required_level: str) -> bool:
        if not self._current_user:
            return False
        level_priority = {
            'admin': 5, 'accountant': 4, 'payroll': 3,
            'inventory': 2, 'viewer': 1,
        }
        current = level_priority.get(self._current_user.get('level', 'viewer'), 0)
        required = level_priority.get(required_level, 0)
        return current >= required
    
    def deny(self, action: str, message: str = None):
        msg = message or f"شما دسترسی لازم برای {action} ندارید"
        self.event_bus.permission_denied.emit(action, msg)


# ============================================================
# AppCore — هسته مرکزی
# ============================================================

class AppCore(QObject):
    """هسته مرکزی برنامه"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.event_bus = EventBus(self)
        self.theme = ThemeService(self.event_bus, self)
        self.ai = AIService(self.event_bus, self)
        self.notifications = NotificationService(self.event_bus, self)
        self.data = DataService(self.event_bus, self)
        self.user = UserService(self.event_bus, self)
        
        self._is_initialized = False
        logger.info("🚀 AppCore راه‌اندازی شد")
    
    def initialize(self):
        if self._is_initialized:
            return
        self._is_initialized = True
        self.event_bus.app_started.emit()
        self.event_bus.app_ready.emit()
        logger.info("✅ AppCore آماده است")
    
    def shutdown(self):
        try:
            self.ai._memory.save()
            self.ai.agent.memory.save()
        except Exception as e:
            logger.warning(f"خطا در ذخیره: {e}")
        
        self.event_bus.app_closing.emit()
        logger.info("👋 AppCore خاموش شد")
    
    def get_stats(self) -> dict:
        return {
            'event_bus': self.event_bus.get_stats(),
            'ai': self.ai.get_status(),
            'agent': self.ai.get_agent_stats(),
            'user': self.user.get_current(),
            'theme': self.theme.get_current(),
            'contexts': self.ai.context_registry.get_stats(),
        }


# ============================================================
# Singleton
# ============================================================

_app_core_instance: Optional[AppCore] = None


def get_app_core() -> AppCore:
    global _app_core_instance
    if _app_core_instance is None:
        _app_core_instance = AppCore()
    return _app_core_instance


def get_event_bus() -> EventBus:
    return get_app_core().event_bus
