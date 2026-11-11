import random
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(page_title="Weather Dashboard", page_icon="🌦️", layout="wide")

# ---------- Weather code -> (description, emoji) ----------
WEATHER_CODES = {
    0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Foggy", "🌫️"), 48: ("Foggy", "🌫️"),
    51: ("Light drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy drizzle", "🌧️"),
    56: ("Freezing drizzle", "🌧️"), 57: ("Freezing drizzle", "🌧️"),
    61: ("Light rain", "🌦️"), 63: ("Rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"), 67: ("Freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"), 73: ("Snow", "❄️"), 75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"), 80: ("Rain showers", "🌦️"), 81: ("Rain showers", "🌧️"),
    82: ("Violent showers", "⛈️"), 85: ("Snow showers", "🌨️"), 86: ("Snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm with hail", "⛈️"),
    99: ("Thunderstorm with hail", "⛈️"),
}
RAIN_CODES = (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82)

GRADIENTS = {
    "clear": "linear-gradient(to bottom, #2b86e8, #7cc4ff)",
    "night": "linear-gradient(to bottom, #0b1026, #1d2b53)",
    "cloudy": "linear-gradient(to bottom, #56637a, #8796ad)",
    "rain": "linear-gradient(to bottom, #1b2430, #3b4d61)",
    "storm": "linear-gradient(to bottom, #0c1015, #2a3340)",
    "snow": "linear-gradient(to bottom, #5c7a9e, #a9bdd6)",
    "fog": "linear-gradient(to bottom, #6b7487, #aab3c2)",
}


def describe(code, is_day):
    text, emoji = WEATHER_CODES.get(code, ("Unknown", "🌡️"))
    if code == 0 and not is_day:
        return "Clear night", "🌙"
    return text, emoji


def get_theme(code, is_day):
    if code in (95, 96, 99):
        return "storm"
    if code in RAIN_CODES:
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (45, 48):
        return "fog"
    if code in (2, 3):
        return "cloudy"
    return "clear" if is_day else "night"


# ---------- Helper functions for the extra information ----------
def compass(degrees):
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[round(degrees / 45) % 8]


def uv_level(uv):
    if uv < 3:
        return "Low"
    if uv < 6:
        return "Moderate"
    if uv < 8:
        return "High"
    if uv < 11:
        return "Very high"
    return "Extreme"


def aqi_level(aqi):
    if aqi <= 50:
        return "Good 🟢"
    if aqi <= 100:
        return "Moderate 🟡"
    if aqi <= 150:
        return "Sensitive 🟠"
    if aqi <= 200:
        return "Unhealthy 🔴"
    if aqi <= 300:
        return "Very bad 🟣"
    return "Hazardous ⚫"


def get_tip(code, temp_c, uv, rain_chance):
    tips = []
    if code in (95, 96, 99):
        tips.append("⚡ Thunderstorms expected. Stay indoors if you can.")
    elif rain_chance >= 50 or code in RAIN_CODES:
        tips.append("☂️ Carry an umbrella.")
    if temp_c >= 33:
        tips.append("🥤 It is very hot. Drink plenty of water.")
    elif temp_c <= 10:
        tips.append("🧥 It is cold. Wear a warm jacket.")
    if uv >= 6:
        tips.append("🧴 Strong sun. Use sunscreen and sunglasses.")
    if not tips:
        tips.append("😊 Pleasant weather. Enjoy your day!")
    return " ".join(tips)


def convert(temp_c, unit):
    if unit == "°F":
        return round(temp_c * 9 / 5 + 32)
    return round(temp_c)


# ---------- Styling ----------
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Poppins', sans-serif; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
.block-container { position: relative; z-index: 1; padding-top: 2rem; }
h1, h2, h3, p, label, span, div[data-testid="stMarkdownContainer"] { color: #ffffff; }
button[data-baseweb="tab"] p { color: #ffffff; font-weight: 600; }
.title { text-align: center; font-size: 2.6rem; font-weight: 700; margin-bottom: 1rem; color: #fff; }
.section { font-size: 1.3rem; font-weight: 600; margin: 1.5rem 0 0.5rem 0; color: #fff; }
.glass {
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 22px;
  padding: 18px;
  text-align: center;
  color: #fff;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  margin-bottom: 12px;
}
.hero .city { font-size: 1.4rem; font-weight: 600; }
.hero .time { font-size: 0.95rem; opacity: 0.85; }
.hero .big-emoji { font-size: 5rem; line-height: 1.1; }
.hero .temp { font-size: 4.5rem; font-weight: 700; line-height: 1; }
.hero .desc { font-size: 1.3rem; font-weight: 300; margin-top: 6px; }
.tip { font-size: 1.05rem; padding: 14px 18px; }
.stat .label { font-size: 0.9rem; opacity: 0.85; }
.stat .value { font-size: 1.6rem; font-weight: 600; }
.stat .sub { font-size: 0.8rem; opacity: 0.75; }
.day .name { font-weight: 600; }
.day .emoji { font-size: 2rem; margin: 4px 0; }
.day .hi { font-weight: 600; }
.day .lo { opacity: 0.75; }
.hourly { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px; }
.hour { min-width: 86px; padding: 12px 8px; }
.hour .name { font-size: 0.85rem; opacity: 0.85; }
.hour .emoji { font-size: 1.7rem; margin: 4px 0; }
.hour .t { font-weight: 600; }
.hour .rain { font-size: 0.75rem; opacity: 0.8; }
.fx { position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none; overflow: hidden; z-index: 0; }
.drop { position: absolute; top: -80px; width: 2px; height: 60px;
        background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(174,194,224,0.8));
        animation: fall linear infinite; }
@keyframes fall { to { transform: translateY(115vh); } }
.flake { position: absolute; top: -10px; background: white; border-radius: 50%;
         opacity: 0.85; animation: snowfall linear infinite; }
@keyframes snowfall { to { transform: translateY(110vh) translateX(50px); } }
.cloud { position: absolute; background: rgba(255,255,255,0.28); border-radius: 100px;
         filter: blur(18px); animation: drift linear infinite; }
@keyframes drift { from { transform: translateX(-45vw); } to { transform: translateX(145vw); } }
.sun { position: absolute; top: 70px; right: 12%; width: 130px; height: 130px; border-radius: 50%;
       background: radial-gradient(circle, #fffbd0 0%, #ffd54f 55%, rgba(255,213,79,0) 72%);
       animation: pulse 4s ease-in-out infinite; }
@keyframes pulse { 0%,100% { transform: scale(1); opacity: 0.95; } 50% { transform: scale(1.12); opacity: 1; } }
.moon { position: absolute; top: 80px; right: 12%; width: 80px; height: 80px; border-radius: 50%;
        background: #f5f3ce; box-shadow: 0 0 50px rgba(245,243,206,0.6); }
.star { position: absolute; background: white; border-radius: 50%; animation: twinkle 3s ease-in-out infinite; }
@keyframes twinkle { 0%,100% { opacity: 0.2; } 50% { opacity: 1; } }
.flash { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: white;
         opacity: 0; animation: flash 7s infinite; }
@keyframes flash { 0%,90%,100% { opacity: 0; } 91% { opacity: 0.55; } 92% { opacity: 0; }
                   94% { opacity: 0.8; } 96% { opacity: 0; } }
/* ---------- Search box ---------- */
[data-baseweb="input"], [data-baseweb="base-input"] {
  background: transparent !important;
  border: none !important;
}
[data-testid="stTextInput"] input {
  background: rgba(255, 255, 255, 0.14) !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  border-radius: 50px !important;
  padding: 14px 24px !important;
  font-size: 1.05rem !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: all 0.35s ease;
}
[data-testid="stTextInput"] input::placeholder { color: rgba(255, 255, 255, 0.65); }
[data-testid="stTextInput"] input:hover {
  background: rgba(255, 255, 255, 0.2) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #ffffff !important;
  transform: scale(1.02);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.18), 0 0 28px rgba(255, 255, 255, 0.35);
  animation: glow 2s ease-in-out infinite;
}
@keyframes glow {
  0%, 100% { box-shadow: 0 0 0 4px rgba(255,255,255,0.15), 0 0 18px rgba(255,255,255,0.25); }
  50%      { box-shadow: 0 0 0 6px rgba(255,255,255,0.25), 0 0 34px rgba(255,255,255,0.45); }
}

/* ---------- C / F toggle ---------- */
[data-testid="stButtonGroup"] button {
  background: rgba(255, 255, 255, 0.14) !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  padding: 12px 22px !important;
  font-weight: 600 !important;
  backdrop-filter: blur(14px);
  transition: all 0.3s ease;
}
[data-testid="stButtonGroup"] button:hover {
  background: rgba(255, 255, 255, 0.28) !important;
  transform: translateY(-2px);
}
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[kind*="Active"] {
  background: #ffffff !important;
  color: #1b2430 !important;
  box-shadow: 0 4px 18px rgba(255, 255, 255, 0.45);
  transform: scale(1.05);
}

/* ---------- Card entrance and hover ---------- */
.glass { animation: fadeUp 0.7s ease both; transition: transform 0.3s ease, box-shadow 0.3s ease; }
.glass:hover { transform: translateY(-6px); box-shadow: 0 14px 38px rgba(0, 0, 0, 0.3); }
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
"""


def make_effects(theme):
    random.seed(7)
    html = ""
    if theme in ("rain", "storm"):
        for _ in range(220 if theme == "storm" else 130):
            html += (f'<div class="drop" style="left:{random.randint(0, 100)}%;'
                     f'animation-delay:{round(random.uniform(0, 2), 2)}s;'
                     f'animation-duration:{round(random.uniform(0.5, 1.1), 2)}s;"></div>')
    if theme == "storm":
        html += '<div class="flash"></div>'
    if theme == "snow":
        for _ in range(90):
            size = random.randint(3, 8)
            html += (f'<div class="flake" style="left:{random.randint(0, 100)}%;'
                     f'width:{size}px;height:{size}px;'
                     f'animation-delay:{round(random.uniform(0, 6), 2)}s;'
                     f'animation-duration:{round(random.uniform(5, 10), 2)}s;"></div>')
    if theme in ("cloudy", "clear", "rain", "storm", "fog"):
        count = 6 if theme in ("cloudy", "fog") else 3
        for _ in range(count):
            html += (f'<div class="cloud" style="top:{random.randint(2, 55)}%;'
                     f'width:{random.randint(220, 420)}px;height:{random.randint(60, 110)}px;'
                     f'animation-duration:{random.randint(45, 90)}s;'
                     f'animation-delay:-{random.randint(0, 60)}s;"></div>')
    if theme == "clear":
        html += '<div class="sun"></div>'
    if theme == "night":
        html += '<div class="moon"></div>'
        for _ in range(70):
            size = random.randint(1, 3)
            html += (f'<div class="star" style="left:{random.randint(0, 100)}%;'
                     f'top:{random.randint(0, 80)}%;width:{size}px;height:{size}px;'
                     f'animation-delay:{round(random.uniform(0, 3), 2)}s;"></div>')
    return f'<div class="fx">{html}</div>'


def apply_theme(theme):
    gradient_css = f"<style>.stApp {{ background: {GRADIENTS[theme]}; }}</style>"
    st.markdown(BASE_CSS + gradient_css + make_effects(theme), unsafe_allow_html=True)


def show_stats(items):
    for col, (label, value, sub) in zip(st.columns(len(items)), items):
        col.markdown(
            f'<div class="glass stat"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )


# ---------- Data ----------
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
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "weather_code,wind_speed_10m,wind_direction_10m,is_day,"
                   "surface_pressure,cloud_cover",
        "hourly": "temperature_2m,weather_code,precipitation_probability,visibility,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,sunrise,sunset,"
                 "daylight_duration,uv_index_max",
        "timezone": "auto",
    }
    try:
        return requests.get(url, params=params, timeout=10).json()
    except requests.exceptions.RequestException:
        st.error("Could not get weather data. Please try again.")
        st.stop()


def get_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5"}
    try:
        return requests.get(url, params=params, timeout=10).json().get("current")
    except Exception:
        return None  # air quality is optional, so the app keeps working without it


# ---------- Page ----------
st.markdown('<div class="title">🌦️ Weather Dashboard</div>', unsafe_allow_html=True)

left, right = st.columns([4, 1])
city = left.text_input(
    "City", "Coimbatore", placeholder="🔍 Search for a city...", label_visibility="collapsed"
)
unit = right.segmented_control(
    "Unit", ["°C", "°F"], default="°C", label_visibility="collapsed"
) or "°C"
place = get_location(city)
if place is None:
    apply_theme("cloudy")
    st.error("City not found. Check the spelling.")
    st.stop()

weather = get_weather(place["latitude"], place["longitude"])
air = get_air_quality(place["latitude"], place["longitude"])
now = weather["current"]
hourly = weather["hourly"]
daily = weather["daily"]

is_day = now["is_day"] == 1
code = now["weather_code"]
desc, emoji = describe(code, is_day)
apply_theme(get_theme(code, is_day))

# Find the current hour in the hourly list
try:
    start = hourly["time"].index(now["time"][:13] + ":00")
except ValueError:
    start = 0

rain_chance = daily["precipitation_probability_max"][0] or 0
uv = daily["uv_index_max"][0] or 0
local_time = datetime.strptime(now["time"], "%Y-%m-%dT%H:%M").strftime("%A, %d %B %Y, %I:%M %p")

# Big main card
st.markdown(
    f'<div class="glass hero">'
    f'<div class="city">📍 {place["name"]}, {place.get("country", "")}</div>'
    f'<div class="time">🕒 {local_time}</div>'
    f'<div class="big-emoji">{emoji}</div>'
    f'<div class="temp">{convert(now["temperature_2m"], unit)}{unit}</div>'
    f'<div class="desc">{desc}</div></div>',
    unsafe_allow_html=True,
)

# Smart tip
tip = get_tip(code, now["temperature_2m"], uv, rain_chance)
st.markdown(f'<div class="glass tip">💡 {tip}</div>', unsafe_allow_html=True)

# Info cards, row 1
show_stats([
    ("🌡️ Feels like", f'{convert(now["apparent_temperature"], unit)}{unit}', "How it feels outside"),
    ("💧 Humidity", f'{now["relative_humidity_2m"]}%', "Moisture in the air"),
    ("💨 Wind", f'{now["wind_speed_10m"]} km/h', f'Direction: {compass(now["wind_direction_10m"])}'),
    ("🌧️ Rain chance", f"{rain_chance}%", "Today"),
])

# Info cards, row 2
visibility_km = round(hourly["visibility"][start] / 1000, 1)
show_stats([
    ("🧭 Pressure", f'{round(now["surface_pressure"])} hPa', "Air pressure"),
    ("👁️ Visibility", f"{visibility_km} km", "How far you can see"),
    ("☁️ Cloud cover", f'{now["cloud_cover"]}%', "Sky covered by clouds"),
    ("🕶️ UV index", f"{round(uv, 1)}", uv_level(uv)),
])

# Info cards, row 3
sunrise = daily["sunrise"][0].split("T")[1]
sunset = daily["sunset"][0].split("T")[1]
hours, minutes = divmod(int(daily["daylight_duration"][0] // 60), 60)
if air and air.get("us_aqi") is not None:
    aqi_value, aqi_sub = str(round(air["us_aqi"])), aqi_level(air["us_aqi"])
else:
    aqi_value, aqi_sub = "N/A", "Not available"
show_stats([
    ("🌅 Sunrise", sunrise, "Morning"),
    ("🌇 Sunset", sunset, "Evening"),
    ("⏳ Daylight", f"{hours}h {minutes}m", "Total today"),
    ("🌫️ Air quality", aqi_value, aqi_sub),
])

# Hourly forecast and chart
st.markdown('<div class="section">⏰ Next 24 Hours</div>', unsafe_allow_html=True)
end = min(start + 24, len(hourly["time"]))
cards = ""
for i in range(start, end):
    label = "Now" if i == start else hourly["time"][i][11:16]
    _, hour_emoji = describe(hourly["weather_code"][i], hourly["is_day"][i] == 1)
    prob = hourly["precipitation_probability"][i] or 0
    cards += (f'<div class="glass hour"><div class="name">{label}</div>'
              f'<div class="emoji">{hour_emoji}</div>'
              f'<div class="t">{convert(hourly["temperature_2m"][i], unit)}°</div>'
              f'<div class="rain">💧 {prob}%</div></div>')
st.markdown(f'<div class="hourly">{cards}</div>', unsafe_allow_html=True)

# 7-day forecast
st.markdown('<div class="section">📅 7-Day Forecast</div>', unsafe_allow_html=True)
for i, col in enumerate(st.columns(7)):
    day_name = "Today" if i == 0 else datetime.strptime(daily["time"][i], "%Y-%m-%d").strftime("%a")
    _, day_emoji = describe(daily["weather_code"][i], True)
    col.markdown(
        f'<div class="glass day"><div class="name">{day_name}</div>'
        f'<div class="emoji">{day_emoji}</div>'
        f'<div class="hi">{convert(daily["temperature_2m_max"][i], unit)}°</div>'
        f'<div class="lo">{convert(daily["temperature_2m_min"][i], unit)}°</div></div>',
        unsafe_allow_html=True,
    )

# Charts
st.markdown('<div class="section">📈 Temperature Trends</div>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["Next 24 hours", "7 days"])
with tab1:
    st.line_chart({f"Temperature ({unit})": [convert(t, unit) for t in hourly["temperature_2m"][start:end]]})
with tab2:
    st.line_chart({
        f"Max ({unit})": [convert(t, unit) for t in daily["temperature_2m_max"]],
        f"Min ({unit})": [convert(t, unit) for t in daily["temperature_2m_min"]],
    })

st.caption("Data from Open-Meteo.com")