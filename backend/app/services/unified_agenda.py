from datetime import date, datetime, time, timezone
import uuid
from sqlalchemy.orm import Session
from app.crud.events import EventRepository
from app.crud.tasks import TaskRepository

class UnifiedAgendaService:
    def __init__(self, db: Session): self.db=db
    def build(self, user_id: uuid.UUID, agenda_date: date):
        start=datetime.combine(agenda_date,time.min,tzinfo=timezone.utc); end=datetime.combine(agenda_date,time.max,tzinfo=timezone.utc)
        events=EventRepository(self.db).daily(user_id,start,end); tasks=TaskRepository(self.db).daily(user_id,start,end)
        meetings=[{"id":str(e.id),"title":e.title,"source":e.provider_name,"starts_at":e.starts_at.isoformat(),"ends_at":e.ends_at.isoformat(),"calendar_name":e.calendar_name,"location":e.location} for e in events]
        task_rows=[{"id":str(t.id),"title":t.title,"source":t.provider_name,"due_at":t.due_at.isoformat() if t.due_at else None,"priority":t.priority,"url":t.url,"is_completed":t.is_completed} for t in tasks]
        timeline=sorted(meetings+task_rows, key=lambda x: x.get("starts_at") or x.get("due_at") or "9999")
        msg=self._message(agenda_date, meetings, task_rows)
        return {"date":agenda_date.isoformat(),"timezone":"Europe/Berlin","stats":{"meeting_count":len(meetings),"task_count":len(task_rows),"total_count":len(meetings)+len(task_rows)},"meetings":meetings,"tasks":task_rows,"timeline":timeline,"channel_messages":[{"channel":"web","subject":f"Daily agenda for {agenda_date}","message":msg},{"channel":"email","subject":f"Daily agenda for {agenda_date}","message":msg},{"channel":"telegram","subject":None,"message":msg}]}
    def _message(self, d, meetings, tasks):
        if not meetings and not tasks: return f"You have no synced meetings or tasks for {d}."
        lines=[f"Daily agenda for {d}", ""]
        if meetings:
            lines.append("Meetings:"); lines += [f"- {m['title']} ({m['source']})" for m in meetings]
        if tasks:
            lines.append("Tasks:"); lines += [f"- {t['title']} ({t['source']})" for t in tasks]
        return "\n".join(lines)
