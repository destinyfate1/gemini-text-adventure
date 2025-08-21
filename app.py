import streamlit as st
import google.generativeai as genai
from github import Github
from github.GithubException import GithubException

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sleep in Aethel", page_icon="⚔️")

# --- API & GITHUB CONFIGURATION ---
try:
    # 1. Permissive Safety Settings to reduce blocks
    safety_settings = {
        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
    }

    # Configure Gemini API
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-pro', safety_settings=safety_settings)

    # Configure GitHub API
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo("destinyfate1/gemini-text-adventure") # IMPORTANT: Change this line
    
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
        # --- FIX #1: Added a check here to prevent writing empty messages to your save file ---
        if message.parts:
            role = "Player" if message.role == "user" else "DM"
            full_story += f"{role}:\n{message.parts[0].text}\n\n"
    return full_story.strip()

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

for message in st.session_state.chat.history[2:]:
    with st.chat_message("human" if message.role == "user" else "ai"):
        # --- FIX #2: This is the primary fix for the crash you saw ---
        # This 'if' statement checks if a message has content before trying to display it.
        if message.parts:
            st.markdown(message.parts[0].text)

if prompt := st.chat_input("What is your next action?"):
    with st.chat_message("human"):
        st.markdown(prompt)
    
    response = st.session_state.chat.send_message(prompt)

    with st.chat_message("ai"):
        try:
            ai_message = response.candidates[0].content.parts[0].text
        except (IndexError, ValueError):
            ai_message = "⚠️ **The AI's response was blocked by a core safety filter.** This can happen even on the lowest setting. Please try a different action or rephrase your last one."
            st.warning(f"Safety feedback: `{response.prompt_feedback}`")

        st.markdown(ai_message)
    st.rerun()

# --- SIDEBAR & SAVE BUTTON ---
with st.sidebar:
    st.header("Game Controls")
    if st.button("💾 Save Progress to GitHub"):
        full_story_text = get_full_story_string(st.session_state.initial_story, st.session_state.chat.history)
        save_progress_to_github(full_story_text)
