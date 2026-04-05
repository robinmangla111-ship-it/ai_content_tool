import streamlit as st
import requests

def generate_audio(text, api_key, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "accept": "audio/mpeg"
    }

    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85,
            "style": 0.2
        }
    }

    r = requests.post(url, json=payload, headers=headers)

    if r.status_code != 200:
        return None, r.text

    return r.content, None


def render():
    st.markdown("# 🗣️ Voice Clone Setup")
    st.markdown("Step-by-step guide to clone your voice for free using ElevenLabs.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 Setup Guide", "🎙️ Recording Tips", "🔌 API Integration"])

    with tab1:
        st.info("Setup guide section here...")

    with tab2:
        st.info("Recording tips section here...")

    with tab3:
        st.markdown("### 🔑 Enter Your ElevenLabs Key")

        el_key = st.text_input("ElevenLabs API Key", type="password", placeholder="sk_...")
        voice_id = st.text_input("Voice ID", placeholder="From ElevenLabs → Voices → your clone → ID")

        st.markdown("### 📝 Enter Text to Convert into Voice")
        text = st.text_area("Text", height=150, placeholder="Type your script here...")

        if st.button("🎧 Generate Audio", use_container_width=True):
            if not el_key or not voice_id or not text.strip():
                st.error("Please enter API Key, Voice ID, and some text.")
            else:
                with st.spinner("Generating voice..."):
                    audio_bytes, err = generate_audio(text, el_key, voice_id)

                if err:
                    st.error("Failed to generate audio")
                    st.code(err)
                else:
                    st.success("Audio generated successfully!")

                    st.audio(audio_bytes, format="audio/mp3")

                    st.download_button(
                        "⬇️ Download MP3",
                        data=audio_bytes,
                        file_name="voice_output.mp3",
                        mime="audio/mpeg",
                        use_container_width=True
                    )


if __name__ == "__main__":
    render()
