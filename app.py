import streamlit as st
import google.generativeai as genai
from github import Github
from github.GithubException import GithubException

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Adventures in Aethel", page_icon="⚔️")

# --- API & GITHUB CONFIGURATION ---
try:
    # Configure Gemini API
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    # Configure GitHub API
    g = Github(st.secrets["GITHUB_TOKEN"])
    # IMPORTANT: Replace with your own GitHub username and repository name
    repo = g.get_repo("destinyfate1/gemini-text-adventure") 
    
except Exception as e:
    st.error(f"Error during initial configuration. Check your secrets. Error: {e}", icon="🚨")
    st.stop()

# --- HELPER FUNCTIONS ---
def get_file_content(file_path, default_content=""):
    """Gets content of a file from the GitHub repo."""
    try:
        file = repo.get_contents(file_path)
        return file.decoded_content.decode("utf-8")
    except GithubException:
        st.warning(f'"{file_path}" not found in the repo. Using default.', icon="⚠️")
        return default_content

def save_progress_to_github(story_string):
    """Saves the story progress back to the 'Story so far.txt' file in GitHub."""
    file_path = "Story so far.txt"
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(
            path=contents.path,
            message="Game progress saved",
            content=story_string,
            sha=contents.sha
        )
        st.sidebar.success("Progress saved to GitHub!")
    except GithubException:
        # If the file doesn't exist, create it
        repo.create_file(
            path=file_path,
            message="Create save file",
            content=story_string
        )
        st.sidebar.success("New save file created on GitHub!")
    except Exception as e:
        st.sidebar.error(f"Failed to save: {e}")

def get_story_string_from_history(chat_history):
    """Formats the chat history into a single string for saving."""
    story_string = ""
    for message in chat_history[2:]: # Skips initial system prompt
        role = "Player" if message.role == "user" else "DM"
        story_string += f"{role}:\n{message.parts[0].text}\n\n"
    return story_string

# --- SESSION STATE INITIALIZATION ---
if "chat" not in st.session_state:
    story_so_far = get_file_content("Story so far.txt", "This is the beginning of a new adventure.")
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
        {'role': 'model', 'parts': ["The world of Aethel is established, the story continues from where we left off. What is your next action?"]}
    ])

# --- UI RENDERING ---
st.title("Total War Gemini")
st.caption("Your progress is loaded directly from GitHub.")

for message in st.session_state.chat.history[2:]:
    with st.chat_message("human" if message.role == "user" else "ai"):
        st.markdown(message.parts[0].text)

if prompt := st.chat_input("What is your next action?"):
    with st.chat_message("human"):
        st.markdown(prompt)
    response = st.session_state.chat.send_message(prompt)
    with st.chat_message("ai"):
        st.markdown(response.text)
    st.rerun()

# --- SIDEBAR & SAVE BUTTON ---
with st.sidebar:
    st.header("Game Controls")
    if st.button("💾 Save Progress to GitHub"):
        story_text = get_story_string_from_history(st.session_state.chat.history)
        save_progress_to_github(story_text)
