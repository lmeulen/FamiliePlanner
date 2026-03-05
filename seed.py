"""
Seed script – clears the database and inserts fresh sample data.
Run:  python seed.py
"""
import asyncio
from datetime import date, datetime, timedelta

from sqlalchemy import delete, insert

from app.config import FAMILY_MEMBERS_DEFAULT
from app.database import AsyncSessionLocal, init_db
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members
from app.models.family import FamilyMember
from app.models.meals import Meal, MealType
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries, task_members


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:

        # ---- Clear all tables (order respects FK constraints) ----
        await db.execute(delete(AgendaEvent))
        await db.execute(delete(RecurrenceSeries))
        await db.execute(delete(Task))
        await db.execute(delete(TaskRecurrenceSeries))
        await db.execute(delete(TaskList))
        await db.execute(delete(Meal))
        await db.execute(delete(FamilyMember))
        await db.commit()
        print("[OK] Database cleared")

        # ---- Family members ----
        for m in FAMILY_MEMBERS_DEFAULT:
            db.add(FamilyMember(id=m["id"], name=m["name"], color=m["color"], avatar=m["avatar"]))
        await db.commit()
        print("[OK] Family members created")

        # ---- Task lists ----
        lists = [
            TaskList(name="Taken",      color="#6C5CE7"),
            TaskList(name="Huishouden", color="#4ECDC4"),
        ]
        db.add_all(lists)
        await db.commit()
        for tl in lists:
            await db.refresh(tl)

        today = date.today()
        tasks_seed = [
            Task(title="Doktersafspraak plannen",  done=False, due_date=today,                    list_id=lists[0].id),
            Task(title="Verzekering nakijken",     done=False, due_date=today + timedelta(days=3), list_id=lists[0].id),
            Task(title="Stofzuigen",               done=False, due_date=today,                    list_id=lists[1].id),
            Task(title="Badkamer schoonmaken",     done=False, due_date=today + timedelta(days=1), list_id=lists[1].id),
            Task(title="Ramen lappen",             done=False, due_date=today + timedelta(days=5), list_id=lists[1].id),
        ]
        db.add_all(tasks_seed)
        await db.flush()
        # Assign member 3 (child) to the first task as example
        await db.execute(task_members.insert().values(task_id=tasks_seed[0].id, member_id=3))
        await db.commit()
        print("[OK] Task lists & tasks created")

        # ---- Agenda events ----
        ev1 = AgendaEvent(
            title="Voetbaltraining",
            start_time=datetime.combine(today, datetime.strptime("16:00", "%H:%M").time()),
            end_time=datetime.combine(today, datetime.strptime("17:30", "%H:%M").time()),
            color="#FF6B6B",
        )
        ev2 = AgendaEvent(
            title="Gezinsavond",
            start_time=datetime.combine(today, datetime.strptime("19:00", "%H:%M").time()),
            end_time=datetime.combine(today, datetime.strptime("21:00", "%H:%M").time()),
            color="#4ECDC4",
        )
        ev3 = AgendaEvent(
            title="Tandarts",
            start_time=datetime.combine(today + timedelta(days=2), datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(today + timedelta(days=2), datetime.strptime("10:30", "%H:%M").time()),
            color="#FF8E53",
        )
        db.add_all([ev1, ev2, ev3])
        await db.flush()
        # Assign members
        await db.execute(agenda_event_members.insert().values(event_id=ev1.id, member_id=3))
        await db.execute(agenda_event_members.insert().values(event_id=ev3.id, member_id=1))
        await db.commit()
        print("[OK] Agenda events created")

        # ---- Meals ----
        db.add_all([
            Meal(date=today,                       meal_type=MealType.breakfast, name="Havermout met fruit"),
            Meal(date=today,                       meal_type=MealType.lunch,     name="Broodjes kaas en ham"),
            Meal(date=today,                       meal_type=MealType.dinner,    name="Spaghetti bolognese"),
            Meal(date=today + timedelta(days=1),   meal_type=MealType.dinner,    name="Kippensoep"),
            Meal(date=today + timedelta(days=2),   meal_type=MealType.dinner,    name="Pizza margherita"),
            Meal(date=today + timedelta(days=3),   meal_type=MealType.dinner,    name="Stamppot boerenkool"),
            Meal(date=today + timedelta(days=4),   meal_type=MealType.dinner,    name="Zalm met groenten"),
        ])
        await db.commit()
        print("[OK] Meals created")

    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
