from __future__ import annotations

import time
from urllib.parse import urljoin

import requests
import streamlit as st

st.set_page_config(page_title="AI Post Generator", page_icon=":brain:", layout="wide")


def _build_url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _get_image_url(api_base: str, relative_path: str) -> str:
    image_file = relative_path.split("/")[-1]
    return _build_url(api_base, f"static/outputs/images/{image_file}")


def _request_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict | list | str]:
    try:
        response = requests.request(method=method, url=url, json=payload, timeout=180)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.status_code, response.json()
        return response.status_code, response.text
    except requests.HTTPError as exc:
        message = exc.response.text if exc.response is not None else str(exc)
        return exc.response.status_code if exc.response is not None else 500, message
    except Exception as exc:
        return 500, str(exc)


st.title(":brain: AI Social Media Post Generator")
st.caption("Generate marketing prompts, captions, hashtags, and AI images")

if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = "http://127.0.0.1:8000"
if "last_generation" not in st.session_state:
    st.session_state.last_generation = None
if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("API Settings")
    api_base_url = st.text_input("FastAPI base URL", value=st.session_state.api_base_url)
    st.session_state.api_base_url = api_base_url
    st.write("API docs: ", _build_url(api_base_url, "/docs"))

    st.divider()

    st.subheader("System Status")
    if st.button("Check Health", use_container_width=True):
        with st.spinner("Checking..."):
            status, data = _request_json("GET", _build_url(api_base_url, "/health"))
            if status == 200:
                st.success(f"API: {data.get('status', 'unknown')}")
                st.info(f"Mode: {data.get('mode', 'unknown')}")
                st.info(f"HuggingFace: {data.get('hf_configured', 'unknown')}")
                hf_info = data.get("hf", {})
                st.caption(f"Text model: {hf_info.get('text_model_configured', 'N/A')}")
                st.caption(f"Image model: {hf_info.get('image_model_configured', 'N/A')}")
            else:
                st.error(f"Health check failed ({status})")
                st.text(data)

    st.divider()

    st.subheader("HF Diagnostics")
    if st.button("View Diagnostics", use_container_width=True):
        with st.spinner("Loading..."):
            status, data = _request_json("GET", _build_url(api_base_url, "/diagnostics/huggingface"))
            if status == 200:
                st.json(data)
            else:
                st.error(f"Failed ({status})")
                st.text(data)

    st.divider()
    st.caption("Built with FastAPI + Streamlit")

tab1, tab2 = st.tabs(["Generate", "History"])

with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Create New Post")

        prompt = st.text_area(
            "Your Idea",
            value="Red chilly pizza with oregano spray for my cafe",
            height=100,
            placeholder="Describe your product or idea..."
        )

        col_size, col_num = st.columns(2)
        with col_size:
            size = st.selectbox("Image Size", options=["1:1", "4:5", "16:9"], index=0)
        with col_num:
            num_images = st.slider("Number of Images", min_value=1, max_value=4, value=2)

        if st.button("Generate Post", type="primary", use_container_width=True):
            if not prompt.strip():
                st.warning("Please enter a prompt")
            else:
                with st.spinner("Generating your post..."):
                    payload = {"prompt": prompt, "size": size, "num_images": num_images}
                    status, data = _request_json("POST", _build_url(api_base_url, "/generate-post"), payload)

                    if status != 200:
                        st.error(f"Generation failed ({status})")
                        if isinstance(data, str):
                            st.text(data[:500])
                    else:
                        st.session_state.last_generation = data
                        st.success("Post generated successfully!")
                        st.json(data)

    with col2:
        st.subheader("Generated Result")

        if st.session_state.last_generation:
            data = st.session_state.last_generation

            st.markdown("**Enhanced Prompt:**")
            st.info(data.get("enhanced_prompt", "N/A"))

            st.markdown("**Caption:**")
            st.success(data.get("caption", "N/A"))

            hashtags = data.get("hashtags", [])
            if hashtags:
                st.markdown("**Hashtags:**")
                st.text(" ".join(hashtags))

            images = data.get("images", [])
            if images:
                st.markdown("**Generated Images:**")
                for i, img in enumerate(images):
                    img_url = _get_image_url(api_base_url, img)
                    st.image(img_url, caption=f"Image {i+1}", use_container_width=True)
        else:
            st.info("Generate a post to see results here")

with tab2:
    st.subheader("Generation History")

    col_btn, col_del = st.columns([1, 4])
    with col_btn:
        if st.button("Refresh History", use_container_width=True):
            st.session_state.history = []

    with st.container():
        status, data = _request_json("GET", _build_url(api_base_url, "/history"))
        if status != 200:
            st.error(f"Could not fetch history ({status})")
            st.text(str(data)[:500])
        elif not data:
            st.info("No generations yet. Create your first post!")
        else:
            st.success(f"Found {len(data)} generation(s)")

            for item in data:
                with st.expander(f"ID: {item['id'][:8]}... | {item['created_at'][:19]}"):
                    st.markdown(f"**Original Prompt:** {item['prompt']}")
                    st.markdown(f"**Enhanced Prompt:** {item['enhanced_prompt']}")
                    st.markdown(f"**Caption:** {item['caption']}")
                    hashtags = item.get("hashtags", [])
                    if hashtags:
                        st.text(" ".join(hashtags))

                    imgs = item.get("images", [])
                    if imgs:
                        cols = st.columns(len(imgs))
                        for idx, img in enumerate(imgs):
                            with cols[idx]:
                                img_url = _get_image_url(api_base_url, img)
                                st.image(img_url, caption=f"Image {idx+1}", use_container_width=True)

                    col_del, _ = st.columns([1, 4])
                    with col_del:
                        if st.button("Delete", key=f"del_{item['id']}"):
                            del_status, del_data = _request_json(
                                "DELETE",
                                _build_url(api_base_url, f"/delete/{item['id']}"),
                            )
                            if del_status == 200:
                                st.success("Deleted!")
                                st.rerun()
                            else:
                                st.error(f"Delete failed ({del_status})")

    st.divider()

    with st.container():
        st.subheader("Delete by ID")
        del_id = st.text_input("Generation ID", placeholder="Enter ID to delete...")
        if st.button("Delete Generation", use_container_width=True):
            if not del_id.strip():
                st.warning("Enter a generation ID")
            else:
                status, data = _request_json("DELETE", _build_url(api_base_url, f"/delete/{del_id.strip()}"))
                if status == 200:
                    st.success("Deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Delete failed ({status})")
                    st.text(str(data)[:200])
