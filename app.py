import random
import streamlit as st
import requests


def add_rain_background(drops=120):
    random.seed(1)  # keeps the raindrops in the same places on every refresh
    drop_html = ""
    for _ in range(drops):
        left = random.randint(0, 100)
        delay = round(random.uniform(0, 2), 2)
        duration = round(random.uniform(0.5, 1.2), 2)
        drop_html += (
            f'<div class="drop" style="left:{left}%; '
            f'animation-delay:{delay}s; animation-duration:{duration}s;"></div>'
        )

    css = """
    <style>
    .stApp {
        background: linear-gradient(to bottom, #1b2430, #3b4d61);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    h1, h2, h3, p, label, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #e8f0f7 !important;
    }
    .rain {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        overflow: hidden;
        z-index: 0;
    }
    .drop {
        position: absolute;
        top: -80px;
        width: 2px;
        height: 60px;
        background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(174,194,224,0.8));
        animation: fall linear infinite;
    }
    @keyframes fall {
        to { transform: translateY(115vh); }
    }
    .block-container {
        position: relative;
        z-index: 1;
    }
    </style>
    """
    st.markdown(css + f'<div class="rain">{drop_html}</div>', unsafe_allow_html=True)


def get_location(city):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    try:
        data = requests.get(url, params={"name": city, "count": 1}, timeout=10).json()
    except requests.exceptions.RequestException:
        st.error("Network problem. Check your internet and try again.")
        st.stop()
    if "results" not in data:
        return None
    return data["results"][0]


def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
    }
    try:
        return requests.get(url, params=params, timeout=10).json()
    except requests.exceptions.RequestException:
        st.error("Could not get weather data. Please try again.")
        st.stop()


def convert(temp_c, unit):
    if unit == "°F":
        return round(temp_c * 9 / 5 + 32, 1)
    return temp_c


add_rain_background()

st.title("🌧️ Weather Dashboard")
city = st.text_input("Enter a city", "Coimbatore")
unit = st.radio("Temperature unit", ["°C", "°F"], horizontal=True)

place = get_location(city)
if place is None:
    st.error("City not found. Check the spelling.")
else:
    weather = get_weather(place["latitude"], place["longitude"])
    st.subheader(f"{place['name']}, {place['country']}")

    temp = convert(weather["current_weather"]["temperature"], unit)
    st.metric("Temperature", f"{temp} {unit}")
    st.metric("Wind speed", f"{weather['current_weather']['windspeed']} km/h")

    daily = weather["daily"]
    chart_data = {
        f"Max ({unit})": [convert(t, unit) for t in daily["temperature_2m_max"]],
        f"Min ({unit})": [convert(t, unit) for t in daily["temperature_2m_min"]],
    }
    st.line_chart(chart_data)