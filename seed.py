"""
Seed script – inserts default family members and sample data.
Run once:  python seed.py
"""
import asyncio
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.config import FAMILY_MEMBERS_DEFAULT
from app.database import AsyncSessionLocal, init_db
from app.models.agenda import AgendaEvent
from app.models.family import FamilyMember
from app.models.meals import Meal, MealType
from app.models.tasks import Task, TaskList


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # ---- Family members ----
        existing = (await db.execute(select(FamilyMember))).scalars().all()
        if not existing:
            for m in FAMILY_MEMBERS_DEFAULT:
                db.add(FamilyMember(id=m["id"], name=m["name"], color=m["color"], avatar=m["avatar"]))
            await db.commit()
            print("✓ Family members created")

        # ---- Task lists ----
        tl_existing = (await db.execute(select(TaskList))).scalars().all()
        if not tl_existing:
            lists = [
                TaskList(name="Boodschappen",   color="#FF6B6B"),
                TaskList(name="Huishouden",     color="#4ECDC4"),
                TaskList(name="School",         color="#6C5CE7"),
            ]
            db.add_all(lists)
            await db.commit()
            await db.refresh(lists[0])
            # Sample tasks
            today = date.today()
            db.add_all([
                Task(title="Melk kopen",         done=False, due_date=today, list_id=lists[0].id),
                Task(title="Brood kopen",         done=False, due_date=today, list_id=lists[0].id),
                Task(title="Stofzuigen",          done=False, due_date=today, list_id=lists[1].id),
                Task(title="Huiswerk wiskunde",   done=False, due_date=today, list_id=lists[2].id, member_id=3),
            ])
            await db.commit()
            print("✓ Task lists & tasks created")

        # ---- Agenda events ----
        ev_existing = (await db.execute(select(AgendaEvent))).scalars().all()
        if not ev_existing:
            today = date.today()
            db.add_all([
                AgendaEvent(
                    title="Voetbaltraining",
                    start_time=datetime.combine(today, datetime.strptime("16:00", "%H:%M").time()),
                    end_time=datetime.combine(today, datetime.strptime("17:30", "%H:%M").time()),
                    color="#FF6B6B",
                    member_id=3,
                ),
                AgendaEvent(
                    title="Gezinsavond",
                    start_time=datetime.combine(today, datetime.strptime("19:00", "%H:%M").time()),
                    end_time=datetime.combine(today, datetime.strptime("21:00", "%H:%M").time()),
                    color="#4ECDC4",
                ),
                AgendaEvent(
                    title="Tandarts",
                    start_time=datetime.combine(today + timedelta(days=2), datetime.strptime("10:00", "%H:%M").time()),
                    end_time=datetime.combine(today + timedelta(days=2), datetime.strptime("10:30", "%H:%M").time()),
                    color="#FF8E53",
                    member_id=1,
                ),
            ])
            await db.commit()
            print("✓ Agenda events created")

        # ---- Meals ----
        meals_existing = (await db.execute(select(Meal))).scalars().all()
        if not meals_existing:
            today = date.today()
            db.add_all([
                Meal(date=today, meal_type=MealType.breakfast, name="Havermout met fruit"),
                Meal(date=today, meal_type=MealType.lunch, name="Broodjes kaas en ham"),
                Meal(date=today, meal_type=MealType.dinner, name="Spaghetti bolognese"),
                Meal(date=today + timedelta(days=1), meal_type=MealType.dinner, name="Kippensoep"),
                Meal(date=today + timedelta(days=2), meal_type=MealType.dinner, name="Pizza margherita"),
                Meal(date=today + timedelta(days=3), meal_type=MealType.dinner, name="Stamppot boerenkool"),
                Meal(date=today + timedelta(days=4), meal_type=MealType.dinner, name="Zalm met groenten"),
            ])
            await db.commit()
            print("✓ Meals created")

    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
