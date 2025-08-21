import streamlit as st
import google.generativeai as genai
# --- NEW: Import the 'types' module for the updated safety settings syntax ---
from google.generativeai import types
from github import Github
from github.GithubException import GithubException
from google.api_core import exceptions

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sleep in Aethel", page_icon="⚔️")

# --- API & GITHUB CONFIGURATION ---
try:
    # --- UPDATED: Safety settings now use the new, more structured format ---
    safety_settings = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    # Configure Gemini API
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Model initialization now uses the new safety_settings list
    model = genai.GenerativeModel('gemini-2.5-pro', safety_settings=safety_settings)

    # Configure GitHub API
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo("destinyfate1/gemini-text-adventure")
    
except Exception as e:
    st.error(f"Error during initial configuration. Check your secrets. Error: {e}", icon="🚨")
    st.stop()

# --- HELPER FUNCTIONS ---

def get_file_content(file_path, default_content=""):
    try:
        file = repo.get_contents(file_path)
        return file.decoded_content.decode("utf-8")
    except GithubException:
        st.warning(f'"{file_path}" not found in the repo. Using default.', icon="⚠️")
        return default_content

def save_progress_to_github(story_string):
    file_path = "Story so far.txt"
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(path=contents.path, message="Game progress saved", content=story_string, sha=contents.sha)
        st.sidebar.success("Progress saved to GitHub!")
    except GithubException:
        repo.create_file(path=file_path, message="Create save file", content=story_string)
        st.sidebar.success("New save file created on GitHub!")
    except Exception as e:
        st.sidebar.error(f"Failed to save: {e}")

def get_full_story_string(initial_story, chat_history):
    full_story = initial_story
    if full_story and not full_story.isspace():
        full_story += "\n\n"
    for message in chat_history[2:]:
        if message.parts:
            role = "Player" if message.role == "user" else "DM"
            full_story += f"{role}:\n{message.parts[0].text}\n\n"
    return full_story.strip()

def get_story_summary(full_story_text, num_interactions=5):
    """
    Extracts the last few interactions (Player + DM turns) from the story log.
    This summary is only for the player to see, the AI gets the full context.
    """
    if not full_story_text or full_story_text.isspace():
        return "No story history to summarize."

    turns = full_story_text.strip().split("Player:")
    if len(turns) < 2:
        turns = full_story_text.strip().split("DM:")

    last_turns = turns[-num_interactions:]
    
    summary = "Player:".join(last_turns).strip()
    if not summary.startswith("Player:") and "DM:" in summary:
         summary = "Player:" + summary

    return f"**Here's a summary of your recent progress:**\n\n---\n\n{summary}\n\n---"


# --- SESSION STATE INITIALIZATION ---
if "chat" not in st.session_state:
    story_so_far = get_file_content("Story so far.txt", "This is the beginning of a new adventure.")
    st.session_state.initial_story = story_so_far
    
    lore_content = get_file_content("lore.html", "No lore was provided.")
    dm_instructions = get_file_content("dm_instructions.txt", "You are a helpful assistant.")

    initial_prompt = f"""
    {dm_instructions}
    HERE IS THE LORE FOR THE WORLD: <lore>{lore_content}</lore>
    HERE IS THE STORY SO FAR: <story>{story_so_far}</story>
    Now, continue the story based on the player's next action.
    """
    
    st.session_state.chat = model.start_chat(history=[
        {'role': 'user', 'parts': [initial_prompt]},
        {'role': 'model', 'parts': ["The world of Aethel is established, and the story continues from where we left off. What is your next action?"]}
    ])

# --- UI RENDERING ---
st.title("⚔️ Adventures in Aethel")
st.caption("Your progress is loaded directly from GitHub.")

if 'initial_story' in st.session_state:
    st.info(get_story_summary(st.session_state.initial_story))

for message in st.session_state.chat.history[2:]:
    with st.chat_message("human" if message.role == "user" else "ai"):
        if message.parts:
            st.markdown(message.parts[0].text)

if prompt := st.chat_input("What is your next action?"):
    with st.chat_message("human"):
        st.markdown(prompt)
    
    try:
        response = st.session_state.chat.send_message(prompt)
        ai_message = response.candidates[0].content.parts[0].text
    except (IndexError, ValueError):
        ai_message = "⚠️ **The AI's response was blocked by a safety filter.** Please try a different action or rephrase your last one."
        st.warning(f"Safety feedback: `{response.prompt_feedback}`")
    except exceptions.InternalServerError:
        ai_message = "⚠️ **Google's servers reported a temporary error.** Please try sending your message again."
    except Exception as e:
        ai_message = f"An unexpected error occurred: {e}"

    with st.chat_message("ai"):
        st.markdown(ai_message)
        
    st.rerun()

# --- SIDEBAR & SAVE BUTTON ---
with st.sidebar:
    st.header("Game Controls")
    if st.button("💾 Save Progress to GitHub"):
        full_story_text = get_full_story_string(st.session_state.initial_story, st.session_state.chat.history)
        save_progress_to_github(full_story_text)
