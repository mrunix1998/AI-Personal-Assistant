from datetime import date, datetime, time, timezone
from sqlalchemy.orm import Session
from app.models.calendar_event import CalendarEvent
from app.models.task_item import TaskItem
from app.schemas.agenda import UnifiedDailyAgenda, MeetingItem, AgendaTaskItem, ChannelMessage

class UnifiedAgendaService:
    def __init__(self, db: Session): self.db=db
    def build_daily_agenda(self, user_id, agenda_date: date) -> UnifiedDailyAgenda:
        start=datetime.combine(agenda_date,time.min,tzinfo=timezone.utc); end=datetime.combine(agenda_date,time.max,tzinfo=timezone.utc)
        events=self.db.query(CalendarEvent).filter(CalendarEvent.user_id==user_id, CalendarEvent.starts_at>=start, CalendarEvent.starts_at<=end).order_by(CalendarEvent.starts_at).all()
        tasks=self.db.query(TaskItem).filter(TaskItem.user_id==user_id, ((TaskItem.due_at>=start)&(TaskItem.due_at<=end)) | (TaskItem.due_at==None)).order_by(TaskItem.due_at.asc().nullslast()).all()  # noqa
        now=datetime.now(timezone.utc)
        meetings=[MeetingItem(id=e.id,title=e.title,source=e.provider_name,calendar_name=e.calendar_name,starts_at=e.starts_at,ends_at=e.ends_at,location=e.location) for e in events]
        task_items=[AgendaTaskItem(id=t.id,title=t.title,source=t.provider_name,due_at=t.due_at,is_completed=t.is_completed,is_overdue=bool(t.due_at and t.due_at < now and not t.is_completed)) for t in tasks]
        stats={"meeting_count":len(meetings),"task_count":len(task_items),"overdue_task_count":sum(1 for t in task_items if t.is_overdue),"completed_task_count":sum(1 for t in task_items if t.is_completed),"total_count":len(meetings)+len(task_items)}
        lines=[]
        for m in meetings: lines.append(f"• {m.starts_at.strftime('%H:%M')} {m.title} ({m.source})")
        for t in task_items: lines.append(f"• Task: {t.title}" + (f" due {t.due_at.strftime('%H:%M')}" if t.due_at else ""))
        msg="You have no synced meetings or tasks for %s."%agenda_date if not lines else "Your agenda for %s:\n%s"%(agenda_date,"\n".join(lines))
        timeline=[{"type":"meeting","time":m.starts_at.isoformat(),"title":m.title,"source":m.source} for m in meetings]+[{"type":"task","time":t.due_at.isoformat() if t.due_at else None,"title":t.title,"source":t.source} for t in task_items]
        cms=[ChannelMessage(channel=c,subject=(f"Daily agenda for {agenda_date}" if c in ["web","email"] else None),message=msg,payload={"total_count":stats["total_count"]}) for c in ["web","email","telegram","web_push"]]
        return UnifiedDailyAgenda(date=agenda_date,stats=stats,meetings=meetings,tasks=task_items,timeline=timeline,channel_messages=cms)
