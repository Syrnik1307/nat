"""Repository abstractions over Cosmos DB containers.

Keep minimal; not replacing ORM yet. Each repo exposes CRUD/queries
aligned with chosen partition keys. In production you would add
concurrency safeguards, ETag matching, and diagnostics logging.
"""
import uuid
from datetime import datetime
from django.utils import timezone
from . import cosmos_db


class BaseRepo:
    container_name = None  # override
    partition_key_field = None  # logical field name present in item dict

    def _container(self):
        return cosmos_db.get_container(self.container_name)

    def _now_iso(self):
        return timezone.now().isoformat()

    def get(self, item_id, partition_key):
        return cosmos_db.read_item(self.container_name, item_id, partition_key)

    def query(self, query, parameters=None):
        return cosmos_db.query_items(self.container_name, query, parameters)

    def upsert(self, item: dict):
        if 'id' not in item:
            item['id'] = str(uuid.uuid4())
        item.setdefault('updated_at', self._now_iso())
        return cosmos_db.upsert_item(self.container_name, item)


class LessonRepo(BaseRepo):
    container_name = 'lessons'
    partition_key_field = 'groupId'

    def to_item(self, lesson):
        return {
            'id': f"lesson_{lesson.id}",
            'groupId': lesson.group_id,
            'title': lesson.title,
            'teacherId': lesson.teacher_id,
            'start_time': lesson.start_time.isoformat(),
            'end_time': lesson.end_time.isoformat(),
            'zoom_meeting_id': lesson.zoom_meeting_id,
            'zoom_account_email': getattr(lesson.zoom_account, 'email', None),
            'created_at': lesson.created_at.isoformat(),
            'updated_at': lesson.updated_at.isoformat(),
        }

    def upsert_from_model(self, lesson):
        item = self.to_item(lesson)
        return self.upsert(item)

    def list_for_group(self, group_id, since_iso=None):
        q = "SELECT * FROM c WHERE c.groupId = @gid"
        params = [{'name': '@gid', 'value': group_id}]
        if since_iso:
            q += " AND c.start_time >= @since"
            params.append({'name': '@since', 'value': since_iso})
        return self.query(q, params)


class ZoomAccountRepo(BaseRepo):
    container_name = 'zoomAccounts'
    partition_key_field = 'zoomAccountId'

    def to_item(self, account):
        return {
            'id': f"zoom_{account.id}",
            'zoomAccountId': account.id,  # partition key value
            'email': account.email,
            'max_concurrent_meetings': account.max_concurrent_meetings,
            'current_meetings': account.current_meetings,
            'is_active': account.is_active,
            'last_used_at': account.last_used_at.isoformat() if account.last_used_at else None,
            'updated_at': account.updated_at.isoformat(),
        }

    def upsert_from_model(self, account):
        return self.upsert(self.to_item(account))


class AttendanceRepo(BaseRepo):
    container_name = 'attendance'
    partition_key_field = 'lessonId'

    def to_item(self, attendance):
        return {
            'id': f"att_{attendance.id}",
            'lessonId': attendance.lesson_id,
            'studentId': attendance.student_id,
            'status': attendance.status,
            'marked_at': attendance.marked_at.isoformat(),
        }

    def upsert_from_model(self, attendance):
        return self.upsert(self.to_item(attendance))

    def list_for_lesson(self, lesson_id):
        return self.query("SELECT * FROM c WHERE c.lessonId = @lid", [{'name': '@lid', 'value': lesson_id}])


# Convenience singletons
lesson_repo = LessonRepo()
zoom_account_repo = ZoomAccountRepo()
attendance_repo = AttendanceRepo()


class AnalyticsEventRepo(BaseRepo):
    """
    Repository for analytics events with automatic TTL (30 days)
    
    Events include:
    - lesson_started, lesson_ended
    - homework_submitted, homework_graded
    - attendance_marked
    - zoom_account_acquired, zoom_account_released
    
    Partition key: eventDate (YYYY-MM-DD) for efficient time-series queries
    TTL: 30 days (auto-deletion from Cosmos DB)
    """
    container_name = 'analyticsEvents'
    partition_key_field = 'eventDate'
    
    def log_event(self, event_type: str, data: dict, timestamp=None):
        """
        Log an analytics event
        
        Args:
            event_type: Type of event (e.g., 'lesson_started', 'homework_submitted')
            data: Event-specific data (lessonId, userId, etc.)
            timestamp: Event timestamp (defaults to now)
        
        Returns:
            Created event item
        """
        if timestamp is None:
            timestamp = timezone.now()
        
        event_date = timestamp.strftime('%Y-%m-%d')
        
        item = {
            'id': str(uuid.uuid4()),
            'eventDate': event_date,  # Partition key
            'eventType': event_type,
            'timestamp': timestamp.isoformat(),
            'data': data,
            'created_at': self._now_iso(),
            # TTL will be applied automatically per container config (30 days)
        }
        
        return self.upsert(item)
    
    def query_events_by_date_range(self, event_type: str, start_date: str, end_date: str):
        """
        Query events by type and date range
        
        Args:
            event_type: Event type to filter
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List of matching events
        """
        query = """
            SELECT * FROM c 
            WHERE c.eventType = @type 
            AND c.eventDate >= @start 
            AND c.eventDate <= @end
            ORDER BY c.timestamp DESC
        """
        params = [
            {'name': '@type', 'value': event_type},
            {'name': '@start', 'value': start_date},
            {'name': '@end', 'value': end_date}
        ]
        return self.query(query, params)
    
    def get_lesson_analytics(self, lesson_id: str):
        """Get all analytics events for a specific lesson"""
        query = "SELECT * FROM c WHERE c.data.lessonId = @lid ORDER BY c.timestamp ASC"
        params = [{'name': '@lid', 'value': lesson_id}]
        return self.query(query, params)


analytics_event_repo = AnalyticsEventRepo()
