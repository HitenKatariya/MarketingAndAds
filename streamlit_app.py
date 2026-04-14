from __future__ import annotations

from urllib.parse import urljoin

import requests
import streamlit as st

st.set_page_config(page_title="AI Post Generator", page_icon="🧠", layout="wide")


def _build_url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _to_public_image_url(api_base: str, relative_path: str) -> str:
    # Backend stores images as outputs/images/<file>.png under backend/outputs.
    image_file = relative_path.split("/")[-1]
    return _build_url(api_base, f"static/images/{image_file}")


def _request_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict | list | str]:
    try:
        response = requests.request(method=method, url=url, json=payload, timeout=120)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.status_code, response.json()
        return response.status_code, response.text
    except requests.HTTPError as exc:
        message = exc.response.text if exc.response is not None else str(exc)
        return exc.response.status_code if exc.response is not None else 500, message
    except Exception as exc:  # pragma: no cover
        return 500, str(exc)


st.title("AI Social Media Post Generator")
st.caption("Streamlit client for your FastAPI backend")

with st.sidebar:
    st.header("API Settings")
    api_base_url = st.text_input("FastAPI base URL", value="http://127.0.0.1:8000")
    st.write("Use the backend docs to inspect all endpoints:")
    st.write(_build_url(api_base_url, "/docs"))

    st.subheader("HF Diagnostics")
    if st.button("Refresh HF Diagnostics"):
        status, data = _request_json("GET", _build_url(api_base_url, "/diagnostics/huggingface"))
        if status == 200:
            st.json(data)
        else:
            st.error(f"Diagnostics failed ({status}): {data}")

health_url = _build_url(api_base_url, "/health")
if st.button("Check API Health"):
    status, data = _request_json("GET", health_url)
    if status == 200:
        st.success(f"API is healthy: {data}")
    else:
        st.error(f"Health check failed ({status}): {data}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Generate Full Post")
    prompt = st.text_area("Prompt", value="Red chilly pizza with oregano spray for my cafe")
    size = st.selectbox("Image size", options=["1:1", "4:5", "16:9"], index=0)
    num_images = st.slider("Number of images", min_value=1, max_value=4, value=2)

    if st.button("Generate Post", type="primary"):
        payload = {"prompt": prompt, "size": size, "num_images": num_images}
        status, data = _request_json("POST", _build_url(api_base_url, "/generate-post"), payload)

        if status != 200:
            st.error(f"Generation failed ({status}): {data}")
        else:
            st.success("Post generated")
            st.json(data)

            images = data.get("images", []) if isinstance(data, dict) else []
            if images:
                st.markdown("### Generated Images")
                image_cols = st.columns(len(images))
                for idx, img in enumerate(images):
                    image_url = _to_public_image_url(api_base_url, img)
                    with image_cols[idx]:
                        st.image(image_url, caption=img, use_container_width=True)

with col2:
    st.subheader("History")

    if st.button("Refresh History"):
        status, data = _request_json("GET", _build_url(api_base_url, "/history"))
        if status != 200:
            st.error(f"Could not fetch history ({status}): {data}")
        elif not data:
            st.info("No history yet")
        else:
            st.success(f"Loaded {len(data)} item(s)")
            for item in data:
                with st.expander(f"{item['id']} | {item['created_at']}"):
                    st.write(f"Prompt: {item['prompt']}")
                    st.write(f"Enhanced: {item['enhanced_prompt']}")
                    st.write(f"Caption: {item['caption']}")
                    st.write("Hashtags: " + " ".join(item.get("hashtags", [])))

                    imgs = item.get("images", [])
                    if imgs:
                        img_cols = st.columns(len(imgs))
                        for idx, img in enumerate(imgs):
                            with img_cols[idx]:
                                st.image(
                                    _to_public_image_url(api_base_url, img),
                                    caption=img,
                                    use_container_width=True,
                                )

    st.subheader("Delete Generation")
    generation_id = st.text_input("Generation ID")
    if st.button("Delete"):
        if not generation_id.strip():
            st.warning("Enter a generation ID")
        else:
            status, data = _request_json(
                "DELETE",
                _build_url(api_base_url, f"/delete/{generation_id.strip()}"),
            )
            if status == 200:
                st.success(data)
            else:
                st.error(f"Delete failed ({status}): {data}")
