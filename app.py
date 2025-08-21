import streamlit as st
import google.generativeai as genai
# --- UPDATED: Using the 'types' module for the new safety setting style ---
from google.generativeai import types
from github import Github
from github.GithubException import GithubException
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Adventures in Aethel", page_icon="⚔️")

# --- API & GITHUB CONFIGURATION ---
try:
    # Configure Gemini API from Streamlit Secrets
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    
    # --- UPDATED: Safety settings now use the list-based style you provided ---
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
    
    model = genai.GenerativeModel(
        model_name='gemini-2.5-pro',
        safety_settings=safety_settings
    )

    # Configure GitHub API from Streamlit Secrets
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo("destinyfate1/gemini-text-adventure") # Your repo
    
except Exception as e:
    st.error(f"Error during initial configuration. Have you set your secrets on Streamlit Community Cloud? Error: {e}", icon="🚨")
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
            message="Game progress saved via web app",
            content=story_string,
            sha=contents.sha
        )
        st.sidebar.success("Progress saved to GitHub!")
    except GithubException:
        repo.create_file(path=file_path, message="Create save file", content=story_string)
        st.sidebar.success("New save file created on GitHub!")
    except Exception as e:
        st.sidebar.error(f"Failed to save: {e}")

def get_full_story_string(initial_story, chat_history):
    """Formats the entire story (initial + new session) into a single string."""
    full_story = initial_story
    if full_story and not full_story.isspace():
        full_story += "\n\n"
    for message in chat_history[2:]:
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
        {'role': 'model', 'parts': ["The world of Aethel is established. I am ready."]}
    ])

# --- UI RENDERING ---
st.title("⚔️ Adventures in Aethel")
st.caption("Your progress is loaded directly from GitHub.")

# Display the chat history from the current session
for message in st.session_state.chat.history[2:]:
    with st.chat_message("human" if message.role == "user" else "ai"):
        if message.parts:
            st.markdown(message.parts[0].text)

# Handle user input
if prompt := st.chat_input("What is your next action?"):
    with st.chat_message("human"):
        st.markdown(prompt)
    
    prompt_lower = prompt.lower()
    if "roll" in prompt_lower:
        st.session_state.chat.history.append({'role': 'user', 'parts': [{'text': prompt}]})
        roll = random.randint(1, 100)
        ai_message = f"[Rolling d100... Result: {roll}]"
        st.session_state.chat.history.append({'role': 'model', 'parts': [{'text': ai_message}]})
        with st.chat_message("ai"):
            st.markdown(ai_message)
    else:
        try:
            # --- FAILSAFE 1: ATTEMPT TO GET RESPONSE ---
            response = st.session_state.chat.send_message(prompt)
            ai_message = response.text
        except ValueError:
            # --- FAILSAFE 2: AUTOMATIC RETRY ON BLOCK ---
            # If the first attempt is blocked, create a new prompt asking the AI to reinterpret.
            retry_prompt = (
                f"My previous action was: '{prompt}'. This action was blocked by a safety filter. "
                "Please interpret this action and describe the outcome in a narratively appropriate, "
                "descriptive, and mature way that adheres to safety guidelines while maintaining a gritty tone."
            )
            try:
                # Send the modified prompt
                response = st.session_state.chat.send_message(retry_prompt)
                ai_message = response.text
            except Exception as e:
                # --- FAILSAFE 3: IMMERSIVE FINAL ERROR ---
                # If even the retry fails, show an in-character message.
                ai_message = f"⚔️ **A strange force seems to prevent that action. The threads of fate resist. Perhaps you should try a different approach?** (Error: {e})"
        except Exception as e:
            ai_message = f"An unexpected error occurred: {e}"

        with st.chat_message("ai"):
            st.markdown(ai_message)

    st.rerun()

# --- SIDEBAR & GAME CONTROLS ---
with st.sidebar:
    st.header("Game Controls")
    
    if st.button("💾 Save Progress to GitHub"):
        full_story_text = get_full_story_string(st.session_state.initial_story, st.session_state.chat.history)
        save_progress_to_github(full_story_text)

    st.markdown("---")

    if len(st.session_state.chat.history) > 2:
        if st.button("🔄 Regenerate Last Response"):
            if st.session_state.chat.history[-1].role == "model":
                st.session_state.chat.history.pop()
                last_user_prompt = st.session_state.chat.history.pop()
                st.session_state.resend_prompt = last_user_prompt.parts[0].text

        if st.button("⏪ Undo Last Turn"):
            if st.session_state.chat.history[-1].role == "model": st.session_state.chat.history.pop()
            if st.session_state.chat.history[-1].role == "user": st.session_state.chat.history.pop()
            st.rerun()

if "resend_prompt" in st.session_state and st.session_state.resend_prompt:
    prompt_to_resend = st.session_state.resend_prompt
    st.session_state.resend_prompt = None
    
    with st.chat_message("human"):
        st.markdown(prompt_to_resend)
    
    try:
        response = st.session_state.chat.send_message(prompt_to_resend)
        ai_message = response.text
    except ValueError:
        ai_message = "⚠️ **The AI's response was blocked by a safety filter.** Please try a different action or rephrase your last one."
    except Exception as e:
        ai_message = f"An unexpected error occurred: {e}"

    with st.chat_message("ai"):
        st.markdown(ai_message)
    st.rerun()
