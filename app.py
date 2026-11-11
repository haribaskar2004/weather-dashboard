import streamlit as st
import requests


def get_location(city):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    data = requests.get(url, params={"name": city, "count": 1}).json()
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
    return requests.get(url, params=params).json()


st.title("🌤️ Weather Dashboard")
city = st.text_input("Enter a city", "Coimbatore")

place = get_location(city)
if place is None:
    st.error("City not found. Check the spelling.")
else:
    weather = get_weather(place["latitude"], place["longitude"])
    st.subheader(f"{place['name']}, {place['country']}")
    st.metric("Temperature", f"{weather['current_weather']['temperature']} °C")
    st.metric("Wind speed", f"{weather['current_weather']['windspeed']} km/h")

    daily = weather["daily"]
    chart_data = {
        "Max": daily["temperature_2m_max"],
        "Min": daily["temperature_2m_min"],
    }
    st.line_chart(chart_data)
