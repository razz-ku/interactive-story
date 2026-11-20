import os
import streamlit as st
import random
from dotenv import load_dotenv
from google import genai
 
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

st.set_page_config(
    page_title="Escape the Castle",
    page_icon="🏰",
    layout="centered"
)
st.title("🏰 Escape the Castle")


if "game_started" not in st.session_state:
    st.session_state.game_started = False

required_game_state = (
    "player_name",
    "health",
    "max_health",
    "inventory",
    "rooms",
    "room_number",
    "result_type",
    "result_message",
    "result_value",
    "action_complete",
)
if st.session_state.game_started and any(
    key not in st.session_state for key in required_game_state
):
    st.session_state.game_started = False


def start_game(name):
    st.session_state.game_started = True
    st.session_state.player_name = name
    st.session_state.health = 5
    st.session_state.max_health = 5
    st.session_state.inventory = ["Torch"]
    st.session_state.rooms = [
        "cell",
        "corridor",
        "crypt",
        "library",
        "guard_room",
        "dungeon",
        "castle_gate",
    ]
    st.session_state.room_number = 0
    st.session_state.result_type = ""
    st.session_state.result_message = ""
    st.session_state.result_value = ""
    st.session_state.action_complete = False


def restart_game():
    st.session_state.clear()
    st.rerun()


def get_current_room():
    return st.session_state.rooms[st.session_state.room_number]


def continue_game():
    st.session_state.result_type = ""
    st.session_state.result_message = ""
    st.session_state.result_value = ""
    st.session_state.action_complete = False
    st.session_state.room_number += 1
    st.rerun()


def set_result(result_type, message, value=""):
    st.session_state.result_type = result_type
    st.session_state.result_message = message
    st.session_state.result_value = value
    st.session_state.action_complete = True
    st.rerun()


def add_item(item):
    if item not in st.session_state.inventory:
        st.session_state.inventory.append(item)


def has_item(item):
    return item in st.session_state.inventory


def remove_item(item):
    if item in st.session_state.inventory:
        st.session_state.inventory.remove(item)


def take_damage(amount):
    old_health = st.session_state.health
    st.session_state.health = max(0, old_health - amount)
    return old_health - st.session_state.health


def heal_player(amount):
    old_health = st.session_state.health
    st.session_state.health = min(st.session_state.max_health, st.session_state.health + amount)
    return st.session_state.health - old_health


def generate_story(room, action, outcome, fallback_message):
    if client is None:
        return fallback_message

    inventory_text = ", ".join(st.session_state.inventory)

    prompt = f"""
You are the storyteller for a dark fantasy
adventure game called Escape the Castle.
 
Player: {st.session_state.player_name}
Room: {room}
Health: {st.session_state.health}/{st.session_state.max_health}
Inventory: {inventory_text}
 
Action:
{action}
 
Outcome:
{outcome}
 
Describe what happens in 30-50 words.
 
Use second person.
Use atmospheric dark fantasy language.
Use present tense.
Stay in the current room; do not describe what happens next.
Do not invent characters, items, or events beyond the action and outcome.
Keep the description clear and suitable for a general audience.
Do not change the outcome.
Do not change health or inventory.
Do not introduce new choices.
"""
    try:
        interaction = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt,
            generation_config={"thinking_level": "minimal"}
        )
        if interaction.output_text:
            return interaction.output_text
        return fallback_message
    except Exception as error:
        st.error(f"Gemini error: {error}")
        return fallback_message

def roll_dice():
    return random.randint(1, 6)


def chance_encounter(button_text, room, action, success_number, success_outcome, success_fallback, failure_outcome, failure_fallback, damage, bonus_item=""):
    if st.button(button_text):
        roll = roll_dice()
        if bonus_item != "" and has_item(bonus_item):
            roll = roll + 2
        if roll >= success_number:
            story = generate_story(room, action, success_outcome, success_fallback)
            set_result("success", story)
        else:
            damage_taken = take_damage(damage)
            story = generate_story(room, action, failure_outcome, failure_fallback)
            set_result("damage", story, damage_taken)


def show_room(title, description):
    st.header(title)
    st.write(description)


def show_player_info():
    st.subheader(f"🧑 {st.session_state.player_name}")

    left, right = st.columns(2)
    with left:
        st.write(
            f"❤️ Health: {st.session_state.health}/"
            f"{st.session_state.max_health}"
        )
    with right:
        inventory = ", ".join(st.session_state.inventory)
        st.write(f"🎒 Inventory: {inventory}")

    if has_item("Healing Potion") and st.session_state.health < st.session_state.max_health:
        if st.button("🧪 Use Healing Potion"):
            healed = heal_player(2)
            remove_item("Healing Potion")
            set_result(
                "heal",
                f"You drink the Healing Potion and recover {healed} health.",
                healed,
            )

    st.caption(
        f"Room {st.session_state.room_number + 1}"
        f" of {len(st.session_state.rooms)}"
    )
    st.divider()


def show_result():
    kind = st.session_state.result_type
    value = st.session_state.result_value

    if kind == "story":
        st.write(st.session_state.result_message)
        return
    if kind == "item":
        st.success(f"🎒 NEW ITEM: {value}")
    elif kind == "damage":
        st.error(f"💔 DAMAGE: You lose {value} health.")
    elif kind == "heal":
        st.success(f"💚 HEALED: You recover {value} health.")
    elif kind == "success":
        st.success("✅ Success!")
    else:
        st.info("The journey continues...")

    st.write(st.session_state.result_message)


def show_continue_button(text="Continue"):
    if st.session_state.health <= 0:
        if st.button("🔄 Play Again"):
            restart_game()
    elif st.button(text):
        continue_game()


if not st.session_state.game_started:
    st.write("You wake beneath an ancient castle. Your goal is to escape.")
    name = st.text_input("What is your name?")

    if st.button("Enter the Castle"):
        if name.strip():
            start_game(name)
            st.rerun()
        else:
            st.warning("Enter your name first.")

    st.stop()


show_player_info()
room = get_current_room()

if st.session_state.health <= 0:
    show_room("💀 Game Over", "Your strength gives out. The castle has claimed another victim.")
    st.error("You did not escape the castle")
    if st.button("🔄 Try Again"):
        restart_game()
    st.stop()

# ROOM 1 - CELL
if room == "cell":
    show_room(
        "🔒 The Cell",
        "You wake on a cold stone floor. The iron door creaks open.",
    )
    if not st.session_state.action_complete:
        if st.button("🚪 Leave the cell"):
            outcome = "The player leaves the cell and enters the corridor."
            story = generate_story(
                "The Cell",
                "leave the cell",
                outcome,
                "You step through the creaking iron door and enter the corridor.",
            )
            set_result("story", story)
    else:
        show_result()
        show_continue_button()


# ROOM 2 - CORRIDOR
elif room == "corridor":
    show_room(
        "🕯️ The Corridor",
        "A wooden cabinet stands beside the staircase.",
    )

    if not st.session_state.action_complete:
        left, right = st.columns(2)

        with left:
            if st.button("🔎 Search the cabinet"):
                add_item("Rusty Dagger")
                outcome = "The player finds and takes a Rusty Dagger from the cabinet."
                story = generate_story(
                    "The Corridor",
                    "search the wooden cabinet and take the Rusty Dagger",
                    outcome,
                    "You find a Rusty Dagger inside the cabinet.",
                )
                set_result(
                    "item",
                    story,
                    "Rusty Dagger",
                )

        with right:
            if st.button("➡️ Ignore it"):
                outcome = "The player leaves the cabinet and walks onwards."
                story = generate_story(
                    "The Corridor",
                    "ignore the cabinet",
                    outcome,
                    "You leave the cabinet and walk onwards.",
                )
                set_result(
                    "story",
                    story,
                )
    else:
        show_result()
        show_continue_button()


# ROOM 3 - CRYPT
elif room == "crypt":
    show_room(
        "⚰️ The Crypt",
        "A metal object glints beside a stone coffin.",
    )

    if not st.session_state.action_complete:
        left, right = st.columns(2)

        with left:
            if st.button("🔎 Investigate"):
                add_item("Iron Key")
                outcome = "The player safely picks up the Iron Key beside the coffin."
                story = generate_story(
                    "The Crypt",
                    "investigate the metal object and take the Iron Key",
                    outcome,
                    "You safely pick up an Iron Key.",
                )
                set_result(
                    "item",
                    story,
                    "Iron Key",
                )

        with right:
            if st.button("🚪 Leave the crypt"):
                outcome = "The player leaves the crypt undisturbed."
                story = generate_story(
                    "The Crypt",
                    "leave the crypt",
                    outcome,
                    "You leave the crypt undisturbed.",
                )
                set_result(
                    "story",
                    story,
                )
    else:
        show_result()
        show_continue_button()


# ROOM 4 - LIBRARY
elif room == "library":
    show_room(
        "📚 The Forgotten Library",
        "A strange green light shines from an old book.",
    )

    if not st.session_state.action_complete:
        left, right = st.columns(2)

        with left:
            if st.button("📖 Read the book"):
                outcome = "The book's pages glow with mysterious symbols."
                story = generate_story(
                    "The Forgotten Library",
                    "read the old book",
                    outcome,
                    "The pages glow with mysterious symbols.",
                )
                set_result(
                    "story",
                    story,
                )

        with right:
            if st.button("🚪 Leave it alone"):
                outcome = "The player decides not to touch the book."
                story = generate_story(
                    "The Forgotten Library",
                    "leave the old book alone",
                    outcome,
                    "You decide not to touch the book.",
                )
                set_result(
                    "story",
                    story,
                )
    else:
        show_result()
        show_continue_button()


# ROOM 5 - GUARD ROOM
elif room == "guard_room":
        show_room("⚔️ The Guard Room", "A ghostly knight blocks the doorway.")
        if "Rusty Dagger" in st.session_state.inventory:
            st.info("⚔️ You are carrying a Rusty Dagger.")
        if not st.session_state.action_complete:
            left, right = st.columns(2)
            with left:
                if st.button("⚔️ Fight the knight"):
                    outcome = "The player defeats the knight and can continue."
                    story = generate_story(
                        "The Guard Room", "fight the ghostly knight", outcome, "You dodge the knight's sword. The armour crashes to the floor."
                    )
                    set_result("success", story)
            with right:
                if st.button("🏃 Run past"):
                    outcome = "The player escapes past the knight without injury."
                    story = generate_story(
                        "The Guard Room", "running past the ghostly knight", outcome, "You sprint past the knight and escape through the doorway."
                    )
                    set_result("success", story)
        else:
            show_result()
            show_continue_button()


# ROOM 6 - DUNGEON
elif room == "dungeon":
    show_room(
        "🧪 The Dungeon",
        "You see a bottle containing red liquid.",
    )

    if not st.session_state.action_complete:
        left, right = st.columns(2)

        with left:
            if st.button("🧪 Take the bottle"):
                add_item("Healing Potion")
                outcome = "The player takes the bottle containing the Healing Potion."
                story = generate_story(
                    "The Dungeon",
                    "take the bottle of red liquid",
                    outcome,
                    "You take the bottle and find a Healing Potion inside.",
                )
                set_result(
                    "item",
                    story,
                    "Healing Potion",
                )

        with right:
            if st.button("➡️ Leave the bottle"):
                outcome = "The player leaves the bottle behind."
                story = generate_story(
                    "The Dungeon",
                    "leave the bottle behind",
                    outcome,
                    "You leave the bottle behind.",
                )
                set_result(
                    "story",
                    story,
                )
    else:
        show_result()
        show_continue_button()


# ROOM 7 - CASTLE GATE
elif room == "castle_gate":
    show_room(
        "🏰 The Castle Gate",
        "The massive gate is locked tight.",
    )

    if not st.session_state.action_complete:
        if "Iron Key" in st.session_state.inventory:
            st.info("🗝️ You are carrying an Iron Key.")

            if st.button("🗝️ Unlock the gate"):
                outcome = "The player unlocks the gate and escapes the castle."
                story = generate_story(
                    "The Castle Gate",
                    "use the Iron Key to unlock the gate",
                    outcome,
                    "You unlock the gate and escape the castle!",
                )
                set_result(
                    "success",
                    story,
                )
        else:
            st.warning("You do not have an Iron Key.")

            if st.button("🧗 Climb the wall"):
                outcome = "The player climbs the wall and escapes the castle."
                story = generate_story(
                    "The Castle Gate",
                    "climb the wall",
                    outcome,
                    "You climb the wall and escape the castle!",
                )
                set_result(
                    "success",
                    story,
                )
    else:
        show_result()

        if st.button("🔄 Play Again"):
            restart_game()
