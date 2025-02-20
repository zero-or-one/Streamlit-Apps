import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import pycountry
import random
import json

# Function to fetch country data from the REST Countries API
@st.cache_data
def fetch_country_data(country_name):
    try:
        country = pycountry.countries.get(name=country_name)
        if country:
            country_code = country.alpha_3
            api_url = f"https://restcountries.com/v3.1/alpha/{country_code}"
            response = requests.get(api_url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()[0]

            # Extract relevant information
            capital = data.get("capital", ["N/A"])[0]
            population = data.get("population", "N/A")
            area = data.get("area", "N/A")
            currencies = data.get("currencies", {})
            currency = ", ".join(currencies.keys()) if currencies else "N/A"
            languages = data.get("languages", {})
            language = ", ".join(languages.values()) if languages else "N/A"
            timezones = ", ".join(data.get("timezones", ["N/A"]))
            borders = data.get("borders", [])
            flag_url = data.get("flags", {}).get("png", "")

            neighboring_countries = []
            for border_code in borders:
                try:
                    neighbor = pycountry.countries.get(alpha_3=border_code)
                    if neighbor:
                        neighboring_countries.append(neighbor.name)
                except:
                    pass

            country_data = {
                "Capital": capital,
                "Population": population,
                "Area (sq km)": area,
                "Currency": currency,
                "Official Language(s)": language,
                "Time Zone(s)": timezones,
                "Neighboring Countries": neighboring_countries,
                "Flag": flag_url,
                "Latitude": data["latlng"][0],
                "Longitude": data["latlng"][1]
            }
            return country_data
        else:
            st.error(f"Country '{country_name}' not found.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

# Function to fetch historical data from the World Bank API
@st.cache_data
def fetch_historical_data(country_code, indicator, start_year, end_year):
    try:
        api_url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?date={start_year}:{end_year}&format=json"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()[1]
        df = pd.DataFrame(data)
        df = df[df['value'].notna()]  # Remove rows with missing values
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching historical data: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

# Function to create a line chart for historical data
def create_historical_chart(data, title, y_axis_label):
    if data is None or data.empty:
        return None

    fig = px.line(data, x="date", y="value", title=title, labels={"value": y_axis_label, "date": "Year"})
    return fig

# Function to get a fun fact for a country
@st.cache_data
def get_fun_fact(country_name):
    with open('data/fun_facts.json', 'w', encoding='utf-8') as f:
        fun_facts = json.load(f)

    return fun_facts.get(country_name, "No fun fact available for this country.")

# Function to display the country's location on a map
@st.cache_data
def display_map(country_data):
    latitude = country_data.get("Latitude")
    longitude = country_data.get("Longitude")

    if latitude is not None and longitude is not None:
        map_data = pd.DataFrame({
            'lat': [latitude],
            'lon': [longitude]
        })
        st.map(map_data, zoom=3)
    else:
        st.write("Could not retrieve map data for this country.")

# Function to create a bar chart of neighboring countries' populations
@st.cache_data
def create_neighbor_population_chart(country_data):
    neighbors = country_data.get("Neighboring Countries", [])
    if not neighbors:
        return None

    neighbor_data = []
    for neighbor_name in neighbors:
        try:
            neighbor = pycountry.countries.get(name=neighbor_name)
            if neighbor:
                neighbor_code = neighbor.alpha_3
                api_url = f"https://restcountries.com/v3.1/alpha/{neighbor_code}"
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()[0]
                population = data.get("population", 0)
                neighbor_data.append({"country": neighbor_name, "population": population})
        except:
            pass

    if not neighbor_data:
        return None

    df = pd.DataFrame(neighbor_data)
    fig = px.bar(df, x="country", y="population", title="Population of Neighboring Countries")
    return fig

# Streamlit App
st.title("Country Statistics Explorer")
st.write("Select one or more countries to compare their statistics.")

country_list = [country.name for country in pycountry.countries]
selected_countries = st.multiselect("Select countries:", options=country_list)

START_YEAR = 2000
END_YEAR = 2020

if selected_countries:
    num_countries = len(selected_countries)
    columns = st.columns(num_countries)

    for i, country_name in enumerate(selected_countries):
        with columns[i]:
            country_data = fetch_country_data(country_name)

            if country_data:
                st.header(country_name)
                st.image(country_data["Flag"], width=200)

                st.subheader("Basic Information")
                st.write(f"**Capital:** {country_data['Capital']}")
                st.write(f"**Population:** {country_data['Population']:,}")
                st.write(f"**Area:** {country_data['Area (sq km)']:,} sq km")
                st.write(f"**Currency:** {country_data['Currency']}")
                st.write(f"**Official Language(s):** {country_data['Official Language(s)']}")
                st.write(f"**Time Zone(s):** {country_data['Time Zone(s)']}")
                st.write(f"**Neighboring Countries:** {', '.join(country_data['Neighboring Countries']) or 'N/A'}")

                # Display map
                st.subheader("Country Location")
                display_map(country_data)

                # Display neighbor population chart
                st.subheader("Neighboring Countries Population")
                neighbor_chart = create_neighbor_population_chart(country_data)
                if neighbor_chart:
                    st.plotly_chart(neighbor_chart)
                else:
                    st.write("No data available for neighboring countries' population.")

                # Fetch and display historical GDP data
                country = pycountry.countries.get(name=country_name)
                if country:
                    country_code = country.alpha_3
                    gdp_data = fetch_historical_data(country_code, "NY.GDP.MKTP.CD", START_YEAR, END_YEAR)
                    gdp_chart = create_historical_chart(gdp_data, f"Historical GDP of {country_name}", "GDP (USD)")
                    if gdp_chart:
                        st.plotly_chart(gdp_chart)
                    else:
                        st.write(f"No historical GDP data available for {country_name}.")

                    # Fetch and display historical population data
                    population_data = fetch_historical_data(country_code, "SP.POP.TOTL", START_YEAR, END_YEAR)
                    population_chart = create_historical_chart(population_data, f"Historical Population of {country_name}", "Population")
                    if population_chart:
                        st.plotly_chart(population_chart)
                    else:
                        st.write(f"No historical population data available for {country_name}.")

                # Display fun fact
                fun_fact = get_fun_fact(country_name)
                st.subheader("Fun Fact")
                st.write(fun_fact)