import re
import streamlit as st
import difflib
import re
import difflib
from pathlib import Path
from collections import OrderedDict

import streamlit as st

REF_FILENAME = "요한계시록.txt"

CHAPTER_RE = re.compile(r"^\s*(\d+)\s*장\s*$")
VERSE_RE = re.compile(r"^\s*(\d+)\s+(.*\S)?\s*$")


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def parse_verses(text: str):
    verses = OrderedDict()
    current_chapter = None
    last_key = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if not stripped:
            continue

        chapter_match = CHAPTER_RE.match(stripped)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            last_key = None
            continue

        verse_match = VERSE_RE.match(line)
        if verse_match and current_chapter is not None:
            verse_num = int(verse_match.group(1))
            verse_text = (verse_match.group(2) or "").strip()
            key = (current_chapter, verse_num)
            verses[key] = verse_text
            last_key = key
            continue

        if last_key is not None:
            verses[last_key] = (verses[last_key] + " " + stripped).strip()

    return verses


def load_text_file(path: Path) -> str:
    encodings = ["utf-8-sig", "utf-8", "cp949"]
    last_error = None

    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except Exception as e:
            last_error = e

    raise RuntimeError(f"파일을 읽지 못했습니다: {path}\n{last_error}")


def format_key(key):
    return f"{key[0]}:{key[1]}"


def find_exact_match_in_other_verse(user_norm: str, ref_verses: dict, current_key):
    if not user_norm:
        return None

    for key, ref_text in ref_verses.items():
        if key == current_key:
            continue
        if normalize(ref_text) == user_norm:
            return key
    return None


def diff_segments(user_text: str, ref_text: str):
    user_norm = normalize(user_text)
    ref_norm = normalize(ref_text)

    matcher = difflib.SequenceMatcher(None, user_norm, ref_norm)
    results = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        user_seg = user_norm[i1:i2]
        ref_seg = ref_norm[j1:j2]

        if tag == "replace":
            results.append(("변경", user_seg, ref_seg))
        elif tag == "delete":
            results.append(("삭제", user_seg, ""))
        elif tag == "insert":
            results.append(("추가", "", ref_seg))

    return results


def compare(ref_verses: dict, user_verses: dict):
    results = []

    for key, user_text in user_verses.items():
        if key not in ref_verses:
            results.append({
                "key": key,
                "type": "missing_key",
                "user_text": user_text,
            })
            continue

        ref_text = ref_verses[key]

        if normalize(user_text) == normalize(ref_text):
            continue

        moved_to = find_exact_match_in_other_verse(normalize(user_text), ref_verses, key)
        changes = diff_segments(user_text, ref_text)

        results.append({
            "key": key,
            "type": "diff",
            "user_text": user_text,
            "ref_text": ref_text,
            "moved_to": moved_to,
            "changes": changes,
        })

    return results


st.set_page_config(page_title="계시록 전장 암기", page_icon="📖", layout="wide")

st.title("계시록 전장 암기")
st.caption("기준 파일: 요한계시록.txt")

st.info(
    """
안내
- 이 사이트는 텍스트 입력만 사용하는 계시록 암송 검사기입니다.
- 소스코드는 공개 저장소에서 확인할 수 있습니다.
- 하나의 절이 끝나 다음 절로 넘어갈때 Enter를 필수로 눌러주세요.
- 절과 글자 사이에 띄어쓰기를 필수로 해주세요. 
Ex) 1 예수 그리스도의 계시라 (O)
1예수그리스도의 계시라 (X)
노원 지역 화이팅 ^^

GitHub:
https://github.com/gyesirok/revelation-memorize
"""
)

base_dir = Path(__file__).resolve().parent
ref_path = base_dir / REF_FILENAME

if not ref_path.exists():
    st.error(f"같은 폴더에 '{REF_FILENAME}' 파일이 있어야 합니다.")
    st.stop()

try:
    ref_text = load_text_file(ref_path)
    ref_verses = parse_verses(ref_text)
except Exception as e:
    st.error(str(e))
    st.stop()

st.markdown(
    """
입력 형식 예시

```text
5장
1 내가 보매 ...
2 또 보매 ...
3 하늘 위에나 ...

띄어쓰기 차이는 무시합니다.
일치하는 절은 표시하지 않습니다.
틀린 절만 표시합니다.
"""
)

user_input = st.text_area(
"암송한 본문을 붙여넣으세요",
height=320,
placeholder="예)\n5장\n1 내가 보매 ...\n2 또 보매 ...",
)

col1, col2 = st.columns([1, 1])

with col1:
    check_clicked = st.button("검사하기", use_container_width=True)

with col2:
    clear_clicked = st.button("입력 지우기", use_container_width=True)

if clear_clicked:
    st.rerun()

if check_clicked:
    if not user_input.strip():
        st.warning("본문을 먼저 입력하세요.")
        st.stop()

    user_verses = parse_verses(user_input)

    if not user_verses:
        st.error("입력된 절을 찾지 못했습니다. 예: '5장', '1 내가 보매 ...'")
        st.stop()

    results = compare(ref_verses, user_verses)

    if not results:
        st.success("입력한 절은 모두 일치합니다.")
        st.stop()

    st.subheader("검사 결과")

    for item in results:
        key_text = format_key(item["key"])

        if item["type"] == "missing_key":
            with st.expander(f"{key_text} - 기준 파일에 없는 절 번호", expanded=True):
                st.write("입력한 절 번호가 기준 파일에 없습니다.")
                st.write(f"사용자 입력: {item['user_text']}")
            continue

        with st.expander(f"{key_text}", expanded=True):
            st.write(f"사용자 입력: {item['user_text']}")
            st.write(f"기준 본문: {item['ref_text']}")

            if item["moved_to"] is not None:
                st.warning(
                    f"절 이동 가능성: 입력한 본문이 기준 {format_key(item['moved_to'])} 와 일치합니다."
                )

            st.write("차이:")
            if item["changes"]:
                for kind, user_seg, ref_seg in item["changes"]:
                    if kind == "변경":
                        st.write(f"- 변경: 사용자 `{user_seg}` → 기준 `{ref_seg}`")
                    elif kind == "삭제":
                        st.write(f"- 삭제: 사용자에만 있음 `{user_seg}`")
                    elif kind == "추가":
                        st.write(f"- 추가: 기준에만 있음 `{ref_seg}`")
            else:
                st.write("- 띄어쓰기 외의 차이를 찾지 못했습니다.")
from pathlib import Path
from collections import OrderedDict

import streamlit as st

REF_FILENAME = "요한계시록.txt"

CHAPTER_RE = re.compile(r"^\s*(\d+)\s*장\s*$")
VERSE_RE = re.compile(r"^\s*(\d+)\s+(.*\S)?\s*$")


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def parse_verses(text: str):
    verses = OrderedDict()
    current_chapter = None
    last_key = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if not stripped:
            continue

        chapter_match = CHAPTER_RE.match(stripped)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            last_key = None
            continue

        verse_match = VERSE_RE.match(line)
        if verse_match and current_chapter is not None:
            verse_num = int(verse_match.group(1))
            verse_text = (verse_match.group(2) or "").strip()
            key = (current_chapter, verse_num)
            verses[key] = verse_text
            last_key = key
            continue

        if last_key is not None:
            verses[last_key] = (verses[last_key] + " " + stripped).strip()

    return verses


def load_text_file(path: Path) -> str:
    encodings = ["utf-8-sig", "utf-8", "cp949"]
    last_error = None

    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except Exception as e:
            last_error = e

    raise RuntimeError(f"파일을 읽지 못했습니다: {path}\n{last_error}")


def format_key(key):
    return f"{key[0]}:{key[1]}"


def find_exact_match_in_other_verse(user_norm: str, ref_verses: dict, current_key):
    if not user_norm:
        return None

    for key, ref_text in ref_verses.items():
        if key == current_key:
            continue
        if normalize(ref_text) == user_norm:
            return key
    return None


def diff_segments(user_text: str, ref_text: str):
    user_norm = normalize(user_text)
    ref_norm = normalize(ref_text)

    matcher = difflib.SequenceMatcher(None, user_norm, ref_norm)
    results = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        user_seg = user_norm[i1:i2]
        ref_seg = ref_norm[j1:j2]

        if tag == "replace":
            results.append(("변경", user_seg, ref_seg))
        elif tag == "delete":
            results.append(("삭제", user_seg, ""))
        elif tag == "insert":
            results.append(("추가", "", ref_seg))

    return results


def compare(ref_verses: dict, user_verses: dict):
    results = []

    for key, user_text in user_verses.items():
        if key not in ref_verses:
            results.append({
                "key": key,
                "type": "missing_key",
                "user_text": user_text,
            })
            continue

        ref_text = ref_verses[key]

        if normalize(user_text) == normalize(ref_text):
            continue

        moved_to = find_exact_match_in_other_verse(normalize(user_text), ref_verses, key)
        changes = diff_segments(user_text, ref_text)

        results.append({
            "key": key,
            "type": "diff",
            "user_text": user_text,
            "ref_text": ref_text,
            "moved_to": moved_to,
            "changes": changes,
        })

    return results


st.set_page_config(page_title="계시록 전장 암기", page_icon="📖", layout="wide")

st.title("계시록 전장 암기")
st.caption("기준 파일: 요한계시록.txt")

st.info(
    """
안내
- 이 사이트는 텍스트 입력만 사용하는 계시록 암송 검사기입니다.
- 파일 업로드 기능은 사용하지 않습니다.
- 소스코드는 공개 저장소에서 확인할 수 있습니다.

GitHub:
https://github.com/gyesirok/revelation-memorize
"""
)

base_dir = Path(__file__).resolve().parent
ref_path = base_dir / REF_FILENAME

if not ref_path.exists():
    st.error(f"같은 폴더에 '{REF_FILENAME}' 파일이 있어야 합니다.")
    st.stop()

try:
    ref_text = load_text_file(ref_path)
    ref_verses = parse_verses(ref_text)
except Exception as e:
    st.error(str(e))
    st.stop()

st.markdown(
    """
입력 형식 예시

```text
5장
1 내가 보매 ...
2 또 보매 ...
3 하늘 위에나 ...

띄어쓰기 차이는 무시합니다.
일치하는 절은 표시하지 않습니다.
틀린 절만 표시합니다.
"""
)

user_input = st.text_area(
"암송한 본문을 붙여넣으세요",
height=320,
placeholder="예)\n5장\n1 내가 보매 ...\n2 또 보매 ...",
)

col1, col2 = st.columns([1, 1])

with col1:
    check_clicked = st.button("검사하기", use_container_width=True)

with col2:
    clear_clicked = st.button("입력 지우기", use_container_width=True)

if clear_clicked:
    st.rerun()

if check_clicked:
    if not user_input.strip():
        st.warning("본문을 먼저 입력하세요.")
        st.stop()

    user_verses = parse_verses(user_input)

    if not user_verses:
        st.error("입력된 절을 찾지 못했습니다. 예: '5장', '1 내가 보매 ...'")
        st.stop()

    results = compare(ref_verses, user_verses)

    if not results:
        st.success("입력한 절은 모두 일치합니다.")
        st.stop()

    st.subheader("검사 결과")

    for item in results:
        key_text = format_key(item["key"])

        if item["type"] == "missing_key":
            with st.expander(f"{key_text} - 기준 파일에 없는 절 번호", expanded=True):
                st.write("입력한 절 번호가 기준 파일에 없습니다.")
                st.write(f"사용자 입력: {item['user_text']}")
            continue

        with st.expander(f"{key_text}", expanded=True):
            st.write(f"사용자 입력: {item['user_text']}")
            st.write(f"기준 본문: {item['ref_text']}")

            if item["moved_to"] is not None:
                st.warning(
                    f"절 이동 가능성: 입력한 본문이 기준 {format_key(item['moved_to'])} 와 일치합니다."
                )

            st.write("차이:")
            if item["changes"]:
                for kind, user_seg, ref_seg in item["changes"]:
                    if kind == "변경":
                        st.write(f"- 변경: 사용자 `{user_seg}` → 기준 `{ref_seg}`")
                    elif kind == "삭제":
                        st.write(f"- 삭제: 사용자에만 있음 `{user_seg}`")
                    elif kind == "추가":
                        st.write(f"- 추가: 기준에만 있음 `{ref_seg}`")
            else:
                st.write("- 띄어쓰기 외의 차이를 찾지 못했습니다.")
