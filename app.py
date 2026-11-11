import streamlit as st
import requests


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


st.title("🌤️ Weather Dashboard")
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