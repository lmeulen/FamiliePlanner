"""
Seed script – clears the database and inserts fresh sample data.
Uses static family members and grocery categories from the live database.
Run:  python -m tools.seed
"""

import asyncio
from datetime import date, datetime, timedelta

from sqlalchemy import delete

from app.database import AsyncSessionLocal, init_db
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members
from app.models.family import FamilyMember
from app.models.grocery import GroceryCategory
from app.models.meals import Meal, MealType
from app.models.settings import AppSetting
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries, task_members

# Static data from live database
FAMILY_MEMBERS = [
    {"id": 1, "name": "Leo", "color": "#ff6b6b", "avatar": "🧒"},
    {"id": 2, "name": "Erna", "color": "#4ECDC4", "avatar": "👩"},
    {"id": 3, "name": "Ruben", "color": "#FFE66D", "avatar": "🧒"},
    {"id": 4, "name": "Thomas", "color": "#6C5CE7", "avatar": "🧒"},
    {"id": 5, "name": "Hayden", "color": "#FF8E53", "avatar": "🧒"},
    {"id": 6, "name": "All", "color": "#000000", "avatar": "🏠"},
    {"id": 7, "name": "Odi", "color": "#808080", "avatar": "🐱"},
    {"id": 8, "name": "Milo", "color": "#c0c0c0", "avatar": "🐱"},
    {"id": 9, "name": "Drakenpaleis", "color": "#ff00ff", "avatar": "🛝"},
]

GROCERY_CATEGORIES = [
    {"id": 1, "name": "Groente & Fruit", "icon": "🥬", "color": "#4CAF50", "sort_order": 10},
    {"id": 2, "name": "Brood & Bakkerij", "icon": "🍞", "color": "#FF9800", "sort_order": 20},
    {"id": 3, "name": "Zuivel", "icon": "🥛", "color": "#2196F3", "sort_order": 30},
    {"id": 4, "name": "Vlees & Vis", "icon": "🥩", "color": "#F44336", "sort_order": 40},
    {"id": 5, "name": "Kaas & Vleeswaren", "icon": "🧀", "color": "#FFC107", "sort_order": 50},
    {"id": 6, "name": "Conserven & Sauzen", "icon": "🥫", "color": "#795548", "sort_order": 60},
    {"id": 7, "name": "Pasta & Rijst", "icon": "🍝", "color": "#FFEB3B", "sort_order": 70},
    {"id": 8, "name": "Koek & Snoep", "icon": "🍪", "color": "#E91E63", "sort_order": 80},
    {"id": 9, "name": "Diepvries", "icon": "🧊", "color": "#00BCD4", "sort_order": 90},
    {"id": 10, "name": "Non-food", "icon": "🧴", "color": "#9E9E9E", "sort_order": 100},
    {"id": 11, "name": "Overig", "icon": "❓", "color": "#9EA7C4", "sort_order": 110},
]


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
        await db.execute(delete(GroceryCategory))
        await db.execute(delete(AppSetting))
        await db.commit()
        print("[OK] Database cleared")

        # ---- Family members ----
        for m in FAMILY_MEMBERS:
            db.add(FamilyMember(id=m["id"], name=m["name"], color=m["color"], avatar=m["avatar"]))
        await db.commit()
        print(f"[OK] {len(FAMILY_MEMBERS)} family members created")

        # ---- Grocery categories ----
        for c in GROCERY_CATEGORIES:
            db.add(
                GroceryCategory(
                    id=c["id"], name=c["name"], icon=c["icon"], color=c["color"], sort_order=c["sort_order"]
                )
            )
        await db.commit()
        print(f"[OK] {len(GROCERY_CATEGORIES)} grocery categories created")

        # ---- Task lists ----
        lists = [
            TaskList(name="Taken", color="#6C5CE7", sort_order=10),
            TaskList(name="Huishouden", color="#4ECDC4", sort_order=20),
        ]
        db.add_all(lists)
        await db.commit()
        for tl in lists:
            await db.refresh(tl)

        # ---- App settings ----
        db.add(AppSetting(key="overdue_sort_order", value="9999"))
        await db.commit()
        print("[OK] App settings created")

        today = date.today()
        tasks_seed = [
            Task(title="Doktersafspraak plannen", done=False, due_date=today, list_id=lists[0].id),
            Task(title="Verzekering nakijken", done=False, due_date=today + timedelta(days=3), list_id=lists[0].id),
            Task(title="Stofzuigen", done=False, due_date=today, list_id=lists[1].id),
            Task(title="Badkamer schoonmaken", done=False, due_date=today + timedelta(days=1), list_id=lists[1].id),
            Task(title="Ramen lappen", done=False, due_date=today + timedelta(days=5), list_id=lists[1].id),
        ]
        db.add_all(tasks_seed)
        await db.flush()
        # Assign Ruben (id=3) to the first task
        await db.execute(task_members.insert().values(task_id=tasks_seed[0].id, member_id=3))
        await db.commit()
        print("[OK] Task lists & tasks created")

        # ---- Agenda events ----
        ev1 = AgendaEvent(
            title="Voetbaltraining",
            start_time=datetime.combine(today, datetime.strptime("16:00", "%H:%M").time()),
            end_time=datetime.combine(today, datetime.strptime("17:30", "%H:%M").time()),
        )
        ev2 = AgendaEvent(
            title="Gezinsavond",
            start_time=datetime.combine(today, datetime.strptime("19:00", "%H:%M").time()),
            end_time=datetime.combine(today, datetime.strptime("21:00", "%H:%M").time()),
        )
        ev3 = AgendaEvent(
            title="Tandarts",
            start_time=datetime.combine(today + timedelta(days=2), datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(today + timedelta(days=2), datetime.strptime("10:30", "%H:%M").time()),
        )
        db.add_all([ev1, ev2, ev3])
        await db.flush()
        # Assign members
        await db.execute(agenda_event_members.insert().values(event_id=ev1.id, member_id=3))  # Ruben
        await db.execute(agenda_event_members.insert().values(event_id=ev3.id, member_id=1))  # Leo
        await db.commit()
        print("[OK] Agenda events created")

        # ---- Meals ----
        db.add_all(
            [
                Meal(date=today, meal_type=MealType.breakfast, name="Havermout met fruit"),
                Meal(date=today, meal_type=MealType.lunch, name="Broodjes kaas en ham"),
                Meal(date=today, meal_type=MealType.dinner, name="Spaghetti bolognese"),
                Meal(date=today + timedelta(days=1), meal_type=MealType.dinner, name="Kippensoep"),
                Meal(date=today + timedelta(days=2), meal_type=MealType.dinner, name="Pizza margherita"),
                Meal(date=today + timedelta(days=3), meal_type=MealType.dinner, name="Stamppot boerenkool"),
                Meal(date=today + timedelta(days=4), meal_type=MealType.dinner, name="Zalm met groenten"),
            ]
        )
        await db.commit()
        print("[OK] Meals created")

    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
