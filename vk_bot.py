import asyncio
import random
import sqlite3
from datetime import datetime, UTC
from contextlib import contextmanager

from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup

TOKEN = "vk1.a.-BTzntO46GkOubI4_KRgcvEL41LVqqoFWO19UtBTEOoRDtCyp1B9ZXhPI4gVG7ZeqJbJi-_BJ660LMkUo130Wa-6FPS_lmvtI-LZk74c5P3Pe9vD0egBeGH5TnBBk5hJDD99EyCBPrKbFR1zH3Fk0OybWeL8EYdEwHitDFLia9EP4BfqT_S5pHff_Hg3MXKaB8zxeyKqTrQKjLESABnGOQ"
DB_PATH = "walks.db"

bot = Bot(token=TOKEN)

# ============================================================
# СОСТОЯНИЯ
# ============================================================
class WalkState(BaseStateGroup):
    CHOOSE_LOCATION = "choose_location"
    CHOOSE_DURATION = "choose_duration"
    WAITING = "waiting"

# ============================================================
# БАЗА ДАННЫХ
# ============================================================

def db_init():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS active_walks (
                peer_id     INTEGER PRIMARY KEY,
                location    TEXT    NOT NULL,
                duration    INTEGER NOT NULL,
                started_at  TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS walk_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_id     INTEGER NOT NULL,
                location    TEXT    NOT NULL,
                duration    INTEGER NOT NULL,
                started_at  TEXT    NOT NULL,
                finished_at TEXT    NOT NULL
            )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def db_save_walk(peer_id: int, location: str, duration: int):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO active_walks (peer_id, location, duration, started_at) VALUES (?, ?, ?, ?)",
            (peer_id, location, duration, datetime.now(UTC).isoformat())
        )

def db_get_walk(peer_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM active_walks WHERE peer_id = ?", (peer_id,)
        ).fetchone()
        return dict(row) if row else None

def db_finish_walk(peer_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM active_walks WHERE peer_id = ?", (peer_id,)
        ).fetchone()
        if row:
            conn.execute(
                """INSERT INTO walk_history (peer_id, location, duration, started_at, finished_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (row["peer_id"], row["location"], row["duration"],
                 row["started_at"], datetime.now(UTC).isoformat())
            )
            conn.execute("DELETE FROM active_walks WHERE peer_id = ?", (peer_id,))

def db_is_walking(peer_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM active_walks WHERE peer_id = ?", (peer_id,)
        ).fetchone()
        return row is not None

# ============================================================
# ЛУТ
# ============================================================

LOOT_TABLE = {
    "Материнский исток": {
        "common": [
            "Прутик", "Гибкая палка", "Палка с листьями", "Камешек",
            "Средний камень", "Крупный камень", "Малые драгоценные камни",
            "Крупный драгоценный камень", "Мох", "Плющ", "Хрупкая кость",
            "Крепкая кость", "Коготь", "Неизвестный череп", "Смола", "Глина"
        ],
        "uncommon": [
            "Шишка", "Головка кирки", "Уголек", "Разрушенное гнездо",
            "Клюв хищной птицы", "Кусок янтаря", "Кусок угля «обычной формы»",
            "Кусок угля «интересной формы»", "Пуговица", "Заклёпка (от одежды)",
            "Обломок породы с прожилками другого цвета", "Пружина", "Карабин",
            "Ржавая жестяная банка из-под консервов", "Кольцо от банки",
            "Кусочек ткани", "Ржавый карманный ножик", "Барсетка (5 ед)"
        ],
        "rare": ["Обычный предмет", "Необычный предмет", "Редкий предмет"],
        "rare_weights": [0.60, 0.30, 0.10],
        "very_rare": [],
    },
    "Территория амбара": {
        "common": [
            "Прочная палка", "Камешек", "Средний камень", "Песок", "Сено",
            "Паутина", "Хрупкая кость", "Коготь", "Пух", "Перо с хвоста",
            "Перо неизвестной птицы"
        ],
        "uncommon": [
            "Старая скорлупа", "Горстка зерна", "Мелкие железяки",
            "Проржавевшая цепь", "Старая подкова", "Мышеловка",
            "Мешок из тряпочки (5 ед)"
        ],
        "rare": ["Обычный предмет", "Необычный предмет", "Редкий предмет"],
        "rare_weights": [0.60, 0.30, 0.10],
        "very_rare": [],
    },
    "Поляна четырех деревьев": {
        "common": [
            "Прутик", "Гибкая палка", "Прочная палка", "Мох", "Лопух", "Смола",
            "Осока", "Вьюнок", "Плющ", "Паутина", "Камешек", "Средний камень",
            "Крупный камень", "Раковина", "Малая ракушка", "Большая ракушка",
            "Песок", "Перо с хвоста", "Перо неизвестной птицы",
            "Неизвестный череп", "Крепкая кость"
        ],
        "uncommon": [
            "Желудь", "Кусок коры с дуба", "Сброшенная змеиная шкурка",
            "Крылья бабочки", "Крылья стрекозы", "Рожок улитки",
            "Птичья лапка", "Потерянный тряпичный кошелёк (3 ед)"
        ],
        "rare": ["Обычный предмет", "Необычный предмет", "Редкий предмет"],
        "rare_weights": [0.60, 0.30, 0.10],
        "very_rare": [],
    },
    "За пределами леса": {
        "common": [
            "Прутик", "Гибкая палка", "Камешек", "Средний камень",
            "Крупный камень", "Песок", "Глина", "Мох", "Паутина",
            "Хрупкая кость", "Крепкая кость", "Неизвестный череп",
            "Коготь", "Перо неизвестной птицы", "Мята"
        ],
        "uncommon": [],
        "rare": ["Обычный предмет", "Необычный предмет", "Редкий предмет"],
        "rare_weights": [0.60, 0.30, 0.10],
        "very_rare": ["Уникальный предмет"],
    },
    "Гнезда двуногих": {
        "common": [
            "Мелкий мусор", "Стекляшки", "Паутина", "Лопух", "Камешек",
            "Малая ракушка", "Хрупкая кость", "Крепкая кость",
            "Неизвестный череп", "Мята"
        ],
        "uncommon": [
            "Белый воняющий псиной пух", "Кошачий корм",
            "Странно пахнущий кошачий корм", "Гвозди", "Игрушечный шарик",
            "Игрушечная мышка", "Консервная банка", "Тряпка", "Объедки",
            "Зуб двуногого", "Заколка", "Резинка для волос",
            "Кольцо (бижутерия)", "Серьга (бижутерия)", "Подвеска (бижутерия)",
            "Осколок зеркала", "Болт", "Гайка", "Фантик",
            "Целлофановый пакет (25 ед, ломается после 3-х использований)",
            "Авоська (5 ед)"
        ],
        "rare": ["Обычный предмет", "Необычный предмет", "Редкий предмет"],
        "rare_weights": [0.60, 0.30, 0.10],
        "very_rare": [],
    },
}

EVENTS_TABLE = {
    "Материнский исток": [
        "Пока вы карабкались по склону, из-под лап выскользнул камень. Вы едва успели зацепиться за выступ. (-5 хп)",
        "В один миг каждая пещера этого странного места вдруг обрела голос. Тёмные щели зашуршали десятками шепчущих голосов, слов или даже отдельных черт которых различить не удалось. Или это просто ветер?",
        "Вам удалось вдоволь отоспаться на одном из навесов над пещерами. (+10 ед опыта к тренировкам)",
        "На внутренней стене пещеры с тупиком вы обнаружили странные каракули и почти стершиеся цветные следы отпечатков лап разного размера. Коснувшись одного из них, вы случайно стираете последний его след.",
        "Ненароком заплутав в пещерах этого места, вы с трудом выбираетесь обратно к солнцу. Теперь темнота кажется осязаемой.",
    ],
    "Территория амбара": [
        "Местная популярность окупается и от одиночки вы узнаете, что на поляне с 4-мя дубами каждое полнолуние проходит совет диких кошачьих племён.",
        "Вы случайно забрели в разлитую лужу дегтя. Шерсть слиплась и ужасно пахнет. (-3 чл на луну)",
        "В стоге сена вы обнаружили целое гнездо мышей. (Позволяет поймать 3 полёвки без броска на удачу поимки)",
        "В стоге сена вы обнаружили целое гнездо полёвок, но вся дичь разбежалась, оставив за собой только крошечные розовые комочки. (Съесть или пощадить)",
        "Случайным образом вы натыкаетесь на чёрного как смоль ворона. Он не рад гостям. Птица выщипывает несколько клочков вашей шерсти и только после этого скрывается в полях.",
        "С забора вы увидели вереницу котов, обходящих пустошь ровно по краю. Им что, заняться больше нечем?",
    ],
    "Поляна четырех деревьев": [
        "Под корнями одного из огромных дубов вы обнаружили белку, которая слишком увлеклась желудями и не заметила вашего приближения. (Поимка белки без броска на удачу нахождения)",
        "На вашу голову падает желудь. Не больно, но неприятно, это же не может случиться дважды? Случается. И трижды.",
    ],
    "За пределами леса": [
        "Тень от деревьев пропала. Яркое, палящее солнце висело над головой, даже не удосужившись прикрыться облачком. (Все участники вылазки испытывают головокружение, хотят пить и могут мыслить спутанно)",
        "Вы шли вдоль гремящей тропы. Вонь этого места настолько впиталась в ваши ноздри, что вы, кажется, не чувствуете больше ничего другого. (-15 к кубику на нахождение дичи на рп день)",
        "В пути вас сопровождала тень парящей над головой птицы. Сорочий треск то и дело вмешивался в ваши разговоры. Хм...",
        "Вам встретилось странное дерево, будто сплетённое из двух стволов сразу. Подойдя к его корням, вы обнаруживаете блестящую монетку.",
        "Дождь настигает вас в самый неудобный момент. Не сумев найти достойного укрытия, вы были вынуждены спрятаться в земляной ложбинке. Теперь от вас пахнет землёй и влагой, а ваша шкура покрыта грязевой корочкой.",
    ],
    "Гнезда двуногих": [
        "Пока вы пробирались между домов двуногих, вас не покидало постоянное чувство чьего-то взгляда.",
        "Убегая от двуногого, вы пробежались по мелким стекляшкам. (-5 хп всем участникам вылазки)",
        "Весь путь вас преследовал отдалённый, гнетущий лай псов, превращающийся в долгое эхо.",
        "В саду одного из двуногих вы нашли куст чудесно пахнущего растения. (+1 ед кошачьей мяты)",
        "Вы перебегали Гремящую Тропу, и свет фар ослепил вас. Успели отпрыгнуть в последний момент.",
        "На заборе вас встретил упитанный домашний кот в ошейнике, который не желает пропускать «блохастого оборванца» через свой сад.",
        "От местных бродяг вы слышали странные бормотания о старой белоснежной кошке.",
    ],
}

DURATION_CONFIG = {
    30:  {"loot": 3,  "events": (1, 1)},
    60:  {"loot": 5,  "events": (1, 2)},
    90:  {"loot": 7,  "events": (2, 2)},
    120: {"loot": 8,  "events": (2, 2)},
    180: {"loot": 10, "events": (3, 3)},
    240: {"loot": 12, "events": (3, 3)},
    300: {"loot": 13, "events": (3, 3)},
    360: {"loot": 14, "events": (4, 4)},
    420: {"loot": 15, "events": (4, 4)},
}

LOCATIONS = list(LOOT_TABLE.keys())
DURATIONS = list(DURATION_CONFIG.keys())

# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def keyboard_locations():
    kb = Keyboard(one_time=True)
    for loc in LOCATIONS:
        kb.add(Text(loc), color=KeyboardButtonColor.PRIMARY)
        kb.row()
    return kb.get_json()

def keyboard_durations():
    kb = Keyboard(one_time=True)
    labels = {
        30: "30 минут",
        60: "60 минут",
        90: "90 минут",
        120: "120 минут",
        180: "180 минут (3 ч)",
        240: "240 минут (4 ч)",
        300: "300 минут (5 ч)",
        360: "360 минут (6 ч)",
        420: "420 минут (7 ч)",
    }
    for mins, label in labels.items():
        kb.add(Text(label), color=KeyboardButtonColor.SECONDARY)
        kb.row()
    return kb.get_json()

# ============================================================
# ГЕНЕРАЦИЯ ЛУТА И СОБЫТИЙ
# ============================================================

def generate_loot(location: str, count: int) -> dict:
    table = LOOT_TABLE[location]
    counts: dict[str, int] = {}
    for _ in range(count):
        roll = random.random()
        if roll < 0.05 and table["very_rare"]:
            item = random.choice(table["very_rare"])
        elif roll < 0.20:
            item = random.choices(table["rare"], weights=table["rare_weights"])[0]
        elif roll < 0.50 and table["uncommon"]:
            item = random.choice(table["uncommon"])
        else:
            item = random.choice(table["common"])
        counts[item] = counts.get(item, 0) + 1
    return counts

def generate_events(location: str, count: int) -> list:
    pool = EVENTS_TABLE.get(location, [])
    if not pool:
        return []
    return random.sample(pool, min(count, len(pool)))

# ============================================================
# ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТА
# ============================================================

def format_result(location: str, duration_minutes: int) -> str:
    cfg = DURATION_CONFIG[duration_minutes]
    loot = generate_loot(location, cfg["loot"])
    ev_min, ev_max = cfg["events"]
    events = generate_events(location, random.randint(ev_min, ev_max))

    hours = duration_minutes // 60
    mins_rest = duration_minutes % 60
    if hours == 0:
        dur_label = f"{duration_minutes} минут"
    elif mins_rest == 0:
        dur_label = f"{duration_minutes} минут ({hours} ч)"
    else:
        dur_label = f"{duration_minutes} минут ({hours} ч {mins_rest} мин)"

    lines = [
        "Вы набродились.",
        f"Локация: {location}.",
        f"Длительность: {dur_label}.",
        "",
    ]
    if loot:
        lines.append("Вы нашли:")
        for item, cnt in loot.items():
            lines.append(f"-- {item} x{cnt}")
    else:
        lines.append("Вы не обнаружили ничего полезного.")

    lines.append("")

    if events:
        lines.append("С вами произошло:")
        for ev in events:
            lines.append(f"-- {ev}")
    else:
        lines.append("Ничего примечательного не произошло.")

    return "\n".join(lines)

# ============================================================
# ТАЙМЕР
# ============================================================

async def walk_timer(peer_id: int, duration_minutes: int, location: str):
    await asyncio.sleep(duration_minutes * 60)
    # Проверяем, что прогулка ещё числится в БД (не была сброшена вручную)
    if not db_is_walking(peer_id):
        return
    result = format_result(location, duration_minutes)
    db_finish_walk(peer_id)
    await bot.state_dispenser.delete(peer_id)
    await bot.api.messages.send(peer_id=peer_id, message=result, random_id=0)

# ============================================================
# ВОССТАНОВЛЕНИЕ ТАЙМЕРОВ ПОСЛЕ РЕСТАРТА
# ============================================================

async def restore_timers():
    """При запуске бота проверяем незавершённые прогулки в БД и досчитываем таймеры."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM active_walks").fetchall()
    for row in rows:
        peer_id = row["peer_id"]
        location = row["location"]
        duration = row["duration"]
        started_at = datetime.fromisoformat(row["started_at"])
        elapsed_seconds = (datetime.now(UTC) - started_at).total_seconds()
        remaining = duration * 60 - elapsed_seconds
        if remaining <= 0:
            # Время уже вышло — сразу финализируем
            result = format_result(location, duration)
            db_finish_walk(peer_id)
            await bot.state_dispenser.delete(peer_id)
            await bot.api.messages.send(peer_id=peer_id, message=result, random_id=0)
        else:
            # Запускаем таймер на оставшееся время
            asyncio.create_task(_delayed_finish(peer_id, location, duration, remaining))

async def _delayed_finish(peer_id: int, location: str, duration: int, remaining_seconds: float):
    await asyncio.sleep(remaining_seconds)
    if not db_is_walking(peer_id):
        return
    result = format_result(location, duration)
    db_finish_walk(peer_id)
    await bot.state_dispenser.delete(peer_id)
    await bot.api.messages.send(peer_id=peer_id, message=result, random_id=0)

# ============================================================
# ХЭНДЛЕРЫ
# ============================================================

@bot.on.message(text="Бродить по округе")
async def start_walk(message: Message):
    peer_id = message.peer_id
    if db_is_walking(peer_id):
        await message.answer("Вы уже бродите. Дождитесь окончания прогулки.")
        return
    await bot.state_dispenser.set(peer_id, WalkState.CHOOSE_LOCATION)
    await message.answer("Выберите локацию:", keyboard=keyboard_locations())

@bot.on.message(state=WalkState.CHOOSE_LOCATION)
async def choose_location(message: Message):
    peer_id = message.peer_id
    text = message.text.strip()
    if text not in LOCATIONS:
        await message.answer("Выберите локацию из предложенных.", keyboard=keyboard_locations())
        return
    # Временно сохраняем выбранную локацию через state payload (используем отдельную мини-таблицу не нужна —
    # сохраним в pending_walks словарь в памяти, т.к. это короткий диалог до подтверждения)
    bot._pending = getattr(bot, "_pending", {})
    bot._pending[peer_id] = text
    await bot.state_dispenser.set(peer_id, WalkState.CHOOSE_DURATION)
    await message.answer(f"Локация: {text}.\nВыберите длительность:", keyboard=keyboard_durations())

@bot.on.message(state=WalkState.CHOOSE_DURATION)
async def choose_duration(message: Message):
    peer_id = message.peer_id
    text = message.text.strip()

    duration = None
    for mins in DURATIONS:
        if text.startswith(str(mins)):
            duration = mins
            break

    if duration is None:
        await message.answer("Выберите длительность из предложенных.", keyboard=keyboard_durations())
        return

    pending = getattr(bot, "_pending", {})
    location = pending.pop(peer_id, None)
    if not location:
        await message.answer("Что-то пошло не так. Напишите \"Бродить по округе\" снова.")
        await bot.state_dispenser.delete(peer_id)
        return

    db_save_walk(peer_id, location, duration)
    await bot.state_dispenser.set(peer_id, WalkState.WAITING)

    hours = duration // 60
    mins_rest = duration % 60
    if hours == 0:
        dur_label = f"{duration} мин"
    elif mins_rest == 0:
        dur_label = f"{duration} мин ({hours} ч)"
    else:
        dur_label = f"{duration} мин ({hours} ч {mins_rest} мин)"

    await message.answer(
        f"Вы отправляетесь бродить.\n"
        f"Локация: {location}.\n"
        f"Длительность: {dur_label}.\n\n"
        f"Уведомление придёт по истечении времени."
    )
    asyncio.create_task(walk_timer(peer_id, duration, location))

# ============================================================
# ЗАПУСК
# ============================================================

async def on_startup():
    db_init()
    await restore_timers()

bot.loop_wrapper.on_startup.append(on_startup)
bot.run_forever()
