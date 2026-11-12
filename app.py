import base64
import html
import random
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
import streamlit as st

st.set_page_config(page_title="Weather Dashboard", page_icon="🌦️", layout="wide")

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


def describe(code, is_day):
    text, emoji = WEATHER_CODES.get(code, ("Unknown", "🌡️"))
    if code == 0 and not is_day:
        return "Clear night", "🌙"
    return text, emoji


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


def get_alerts(code, now, uv, rain_chance, air):
    alerts = []
    if code in (95, 96, 99):
        alerts.append(("⛈️", "Thunderstorm warning", "Avoid open areas and tall trees."))
    if now["temperature_2m"] >= 38 or now["apparent_temperature"] >= 41:
        alerts.append(("🔥", "Extreme heat", "Stay hydrated and avoid going out at noon."))
    if rain_chance >= 70:
        alerts.append(("🌧️", "Heavy rain likely", "Carry an umbrella and watch for waterlogging."))
    if uv >= 8:
        alerts.append(("🕶️", "Very strong UV", "Use sunscreen and cover up outdoors."))
    if now["wind_speed_10m"] >= 40:
        alerts.append(("💨", "Strong winds", "Secure loose items outside."))
    if air and air.get("us_aqi") is not None and air["us_aqi"] > 150:
        alerts.append(("🌫️", "Poor air quality", "Limit outdoor activity and consider a mask."))
    return alerts


def convert(temp_c, unit):
    if unit == "°F":
        return round(temp_c * 9 / 5 + 32)
    return round(temp_c)


BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Poppins', sans-serif; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
.block-container { position: relative; z-index: 1; padding-top: 2rem; }
h1, h2, h3, p, label, span, div[data-testid="stMarkdownContainer"] { color: #ffffff; }
button[data-baseweb="tab"] p { color: #ffffff; font-weight: 600; }
.title { text-align: center; font-size: 2.6rem; font-weight: 700; margin-bottom: 1rem; color: #fff;
         text-shadow: 0 4px 20px rgba(0,0,0,0.6); }
.section { font-size: 1.3rem; font-weight: 600; margin: 1.5rem 0 0.5rem 0; color: #fff;
           text-shadow: 0 2px 12px rgba(0,0,0,0.6); }
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

/* ---------- Search box (purple) ---------- */
[data-baseweb="input"], [data-baseweb="base-input"] {
  background: transparent !important;
  border: none !important;
}
[data-testid="stTextInput"] input {
  background: rgba(124, 58, 237, 0.45) !important;
  color: #ffffff !important;
  border: 2px solid #c4b5fd !important;
  border-radius: 50px !important;
  padding: 14px 24px !important;
  font-size: 1.05rem !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: all 0.35s ease;
}
[data-testid="stTextInput"] input::placeholder { color: rgba(255, 255, 255, 0.75); }
[data-testid="stTextInput"] input:hover {
  background: rgba(124, 58, 237, 0.6) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #ffffff !important;
  transform: scale(1.02);
  box-shadow: 0 0 0 4px rgba(196, 181, 253, 0.35), 0 0 28px rgba(167, 139, 250, 0.7);
  animation: glow 2s ease-in-out infinite;
}
@keyframes glow {
  0%, 100% { box-shadow: 0 0 0 4px rgba(196,181,253,0.3), 0 0 18px rgba(167,139,250,0.5); }
  50%      { box-shadow: 0 0 0 6px rgba(196,181,253,0.45), 0 0 34px rgba(167,139,250,0.8); }
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

/* ---------- Quick city buttons ---------- */
[data-testid="stButton"] button {
  background: rgba(255, 255, 255, 0.14);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  backdrop-filter: blur(14px);
  transition: all 0.3s ease;
}
[data-testid="stButton"] button:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: #ffffff;
  transform: translateY(-2px);
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

# ---------- Realistic photo / video background ----------
REAL_CSS = """
.stApp { background: #06100b; }
.bgwrap { position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
.bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
      filter: brightness(0.62) contrast(1.08) saturate(1.1); }
img.bg, div.bg { animation: slowzoom 45s ease-in-out infinite alternate; }
@keyframes slowzoom { from { transform: scale(1.0); } to { transform: scale(1.1); } }
.shade { position: absolute; inset: 0;
  background: linear-gradient(to bottom, rgba(0,12,6,0.55), rgba(0,12,6,0.10) 40%, rgba(0,12,6,0.65)); }
.vignette { position: absolute; inset: 0;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.75) 100%); }
.mist { position: absolute; left: 0; bottom: 0; width: 220%; height: 40%;
  background: linear-gradient(to top, rgba(205,230,220,0.22), rgba(205,230,220,0));
  animation: mistmove 50s linear infinite alternate; }
@keyframes mistmove { from { transform: translateX(-45%); } to { transform: translateX(0); } }
.rain { position: absolute; top: -120px; width: 1px;
  background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(215,230,245,0.55));
  animation: realrain linear infinite; }
@keyframes realrain {
  from { transform: translate3d(0, 0, 0) rotate(9deg); }
  to   { transform: translate3d(-14vh, 120vh, 0) rotate(9deg); }
}
.glass { background: rgba(0, 0, 0, 0.38) !important; border-color: rgba(255,255,255,0.18) !important; }
"""


@st.cache_data
def load_background():
    folder = Path(__file__).parent
    options = [
        ("forest.mp4", "video/mp4"),
        ("forest.jpg", "image/jpeg"),
        ("forest.jpeg", "image/jpeg"),
        ("forest.png", "image/png"),
        ("forest.webp", "image/webp"),
    ]
    for name, mime in options:
        path = folder / name
        if path.exists():
            return mime, base64.b64encode(path.read_bytes()).decode()
    return None, None


def apply_theme(theme):
    random.seed(5)
    mime, data = load_background()
    if data is None:
        media = ""
        st.info("Add a photo named forest.jpg to the weather-dashboard folder for the realistic background.")
    elif mime == "video/mp4":
        media = (f'<video class="bg" autoplay muted loop playsinline '
                 f'src="data:video/mp4;base64,{data}"></video>')
    else:
        media = (f'<div class="bg" style="background:url(data:{mime};base64,{data}) '
                 f'center/cover no-repeat;"></div>')

    drops = ""
    for _ in range(170):
        h = random.randint(40, 110)
        blur = random.choice([0, 0, 0.6, 1.2])
        drops += (f'<div class="rain" style="left:{random.randint(0, 115)}%;height:{h}px;'
                  f'opacity:{round(random.uniform(0.25, 0.7), 2)};filter:blur({blur}px);'
                  f'animation-delay:-{round(random.uniform(0, 2), 2)}s;'
                  f'animation-duration:{round(random.uniform(0.55, 1.0), 2)}s;"></div>')

    scene = (f'<div class="bgwrap">{media}<div class="shade"></div>'
             f'<div class="mist"></div>{drops}<div class="vignette"></div></div>')
    st.markdown(BASE_CSS + "<style>" + REAL_CSS + "</style>" + scene, unsafe_allow_html=True)


def show_stats(items):
    for col, (label, value, sub) in zip(st.columns(len(items)), items):
        col.markdown(
            f'<div class="glass stat"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )


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
        return None


@st.cache_data(ttl=1800)
def get_news(query, limit=8):
    url = (
        "https://news.google.com/rss/search?q=" + quote(query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(response.content)
    except Exception:
        return []
    items = []
    for item in root.iter("item"):
        items.append({
            "title": item.findtext("title", ""),
            "link": item.findtext("link", ""),
            "date": item.findtext("pubDate", "")[:16],
        })
        if len(items) >= limit:
            break
    return items


NEWS_TOPICS = {
    "🌍 Climate change": "Tamil Nadu climate change",
    "🌧️ Rain and floods": "Tamil Nadu rain flood",
    "🔥 Heatwave": "Tamil Nadu heatwave temperature",
    "🌀 Cyclone": "Tamil Nadu cyclone",
}


def pick_city(name):
    st.session_state.city = name


# ---------- Page ----------
apply_theme("forest")
st.markdown('<div class="title">🌦️ Weather Dashboard</div>', unsafe_allow_html=True)

if "city" not in st.session_state:
    st.session_state.city = "Coimbatore"

left, right = st.columns([4, 1])
city = left.text_input(
    "City", key="city", placeholder="🔍 Search for a city...", label_visibility="collapsed"
)
unit = right.segmented_control(
    "Unit", ["°C", "°F"], default="°C", label_visibility="collapsed"
) or "°C"

quick_cities = ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Ooty"]
for col, name in zip(st.columns(len(quick_cities)), quick_cities):
    col.button(name, on_click=pick_city, args=(name,), use_container_width=True)

place = get_location(city)
if place is None:
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

try:
    start = hourly["time"].index(now["time"][:13] + ":00")
except ValueError:
    start = 0

rain_chance = daily["precipitation_probability_max"][0] or 0
uv = daily["uv_index_max"][0] or 0
local_time = datetime.strptime(now["time"], "%Y-%m-%dT%H:%M").strftime("%A, %d %B %Y, %I:%M %p")

st.markdown(
    f'<div class="glass hero">'
    f'<div class="city">📍 {place["name"]}, {place.get("country", "")}</div>'
    f'<div class="time">🕒 {local_time}</div>'
    f'<div class="big-emoji">{emoji}</div>'
    f'<div class="temp">{convert(now["temperature_2m"], unit)}{unit}</div>'
    f'<div class="desc">{desc}</div></div>',
    unsafe_allow_html=True,
)

tip = get_tip(code, now["temperature_2m"], uv, rain_chance)
st.markdown(f'<div class="glass tip">💡 {tip}</div>', unsafe_allow_html=True)

for icon, title, message in get_alerts(code, now, uv, rain_chance, air):
    st.markdown(
        f'<div class="glass" style="text-align:left; border-left:6px solid #ffb703;">'
        f'<b>{icon} {title}</b><br>{message}</div>',
        unsafe_allow_html=True,
    )

show_stats([
    ("🌡️ Feels like", f'{convert(now["apparent_temperature"], unit)}{unit}', "How it feels outside"),
    ("💧 Humidity", f'{now["relative_humidity_2m"]}%', "Moisture in the air"),
    ("💨 Wind", f'{now["wind_speed_10m"]} km/h', f'Direction: {compass(now["wind_direction_10m"])}'),
    ("🌧️ Rain chance", f"{rain_chance}%", "Today"),
])

visibility_km = round(hourly["visibility"][start] / 1000, 1)
show_stats([
    ("🧭 Pressure", f'{round(now["surface_pressure"])} hPa', "Air pressure"),
    ("👁️ Visibility", f"{visibility_km} km", "How far you can see"),
    ("☁️ Cloud cover", f'{now["cloud_cover"]}%', "Sky covered by clouds"),
    ("🕶️ UV index", f"{round(uv, 1)}", uv_level(uv)),
])

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

st.markdown('<div class="section">📈 Temperature Trends</div>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["Next 24 hours", "7 days"])
with tab1:
    st.line_chart({f"Temperature ({unit})": [convert(t, unit) for t in hourly["temperature_2m"][start:end]]})
with tab2:
    st.line_chart({
        f"Max ({unit})": [convert(t, unit) for t in daily["temperature_2m_max"]],
        f"Min ({unit})": [convert(t, unit) for t in daily["temperature_2m_min"]],
    })

# ---------- Tamil Nadu climate news ----------
st.markdown('<div class="section">📰 Tamil Nadu Climate News</div>', unsafe_allow_html=True)
topic = st.selectbox("News topic", list(NEWS_TOPICS), label_visibility="collapsed")
news = get_news(NEWS_TOPICS[topic])

if not news:
    st.info("Could not load news right now. Check your internet and try again.")
else:
    for n in news:
        st.markdown(
            f'<div class="glass" style="text-align:left; padding:14px 18px;">'
            f'<a href="{html.escape(n["link"])}" target="_blank" '
            f'style="color:#ffffff; font-weight:600; text-decoration:none;">'
            f'{html.escape(n["title"])}</a>'
            f'<div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">🕒 {n["date"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.caption("Headlines from Google News. Click a headline to read the full story.")

st.caption("Data from Open-Meteo.com")