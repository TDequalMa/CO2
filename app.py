import time
import streamlit as st

st.set_page_config(page_title="교실 CO₂ 환기 알림", page_icon="🌬️")

# 추세선 식: y = a*x + b (x: 재실 인원, y: 평균 분당 CO₂ 변화량, ppm/분)
# 스프레드시트 산점도에 표시된 식이며 R² ≤ 0.2 이므로 참고용 추정이다.
MODELS = {
    "closed": {"label": "창문 닫힘(비환기, None_v)", "a": 0.0507, "b": 12.7},
    "SS": {"label": "한쪽 환기(SS)", "a": -0.233, "b": 4.25},
    "Cross": {"label": "맞통풍(Cross)", "a": 0.268, "b": -8.34},
}


def rate(mode, people):
    m = MODELS[mode]
    return m["a"] * people + m["b"]


st.title("🌬️ 교실 CO₂ 환기 알림")
st.caption(
    "재실 인원·창문 상태에 따른 CO₂ 변화율(추세선)로 기준 도달 시간을 추정하고, "
    "측정값이 기준을 넘으면 환기 알림을 보냅니다."
)

# 입력
col1, col2 = st.columns(2)
people = col1.number_input("재실 인원(명)", min_value=1, max_value=60, value=20, step=1)
threshold = col2.number_input(
    "환기 알림 기준(ppm)", min_value=500, max_value=3000, value=1000, step=50,
    help="집중력 저하를 확정하는 값이 아니라, 사용자가 정한 환기 알림 기준입니다.",
)

window = st.radio("창문 상태", ["닫힘", "열림"], horizontal=True)
if window == "열림":
    kind = st.radio(
        "열린 방식",
        ["한쪽 환기(SS) - 교실 한쪽 면만 개방", "맞통풍(Cross) - 양쪽 면 개방"],
    )
    mode = "SS" if kind.startswith("한쪽") else "Cross"
else:
    mode = "closed"

current = st.number_input(
    "현재 측정한 CO₂(ppm)", min_value=300, max_value=5000, value=800, step=10,
    help="CO₂ 측정기를 보고 입력합니다. 값이 바뀔 때마다 갱신하세요.",
)

# 조건이 바뀌면 그 시점의 농도에서 새 변화율을 적용
state = (people, mode, current)
if st.session_state.get("state") != state:
    st.session_state["state"] = state
    st.session_state["t0"] = time.time()
    st.session_state["c0"] = current

r = rate(mode, people)


@st.fragment(run_every=5)
def monitor():
    elapsed_min = (time.time() - st.session_state["t0"]) / 60
    est = st.session_state["c0"] + r * elapsed_min  # 회귀 기반 추정치

    st.subheader("결과")
    st.metric("추세선 기반 평균 변화율", f"{r:+.2f} ppm/분")

    # 알림은 '측정값' 기준
    if current >= threshold:
        st.error(f"🚨 측정값 {current} ppm이 기준 {threshold} ppm 이상입니다. 환기하세요.")
        st.toast("환기가 필요합니다!", icon="🚨")
    elif r > 0:
        remain = (threshold - current) / r
        left = max(remain - elapsed_min, 0)
        st.info(f"이 조건이 유지되면 약 {left:.0f}분 뒤 기준({threshold} ppm)에 닿을 것으로 추정됩니다.")
        st.caption(f"현재 추정 농도(참고): {est:.0f} ppm — 실제 측정값으로 계속 보정하세요.")
        if left <= 2:
            st.warning("⏰ 곧 기준에 도달할 수 있습니다. 측정값을 확인하세요.")
    else:
        st.success("이 조건에서는 평균적으로 농도가 줄거나 유지되는 추세입니다(추정).")


monitor()

st.divider()
st.markdown(
    "**사용상 주의**  \n"
    "- 변화율은 추세선 식(R² ≤ 0.2)에서 나온 **참고용 추정**이며, 교실 부피·날짜 등은 반영하지 못했습니다.  \n"
    "- 알림은 **직접 입력한 측정값**이 기준 이상일 때 울립니다. 추정치만으로 환기를 판단하지 마세요.  \n"
    "- 식은 관측된 인원 범위 밖에서는 신뢰할 수 없습니다."
)
