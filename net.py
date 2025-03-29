import requests
from bs4 import BeautifulSoup
import json

def replace_logo_link(logo_url):
    """Replace specific logo link with a new link."""
    if logo_url == 'https://img.thesports.com/football/team/0a11e714b8ccb1e287520857bd6cf01c.png':
        return 'https://football.redsport.live//storage/01HQNMEPGZC4XHY6ZWW022VAYN.png'
    return logo_url

# API Endpoint
api_url = "https://aesport.tv/?s_key=Liverpool"

# Send request to API
response = requests.get(api_url)

# Check if the request was successful
if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all match items
    matches = soup.find_all("div", class_="row-item-match")

    # Extract data
    match_data = []
    for match in matches:
        home_team = match.find("span", class_="name-team-left").text.strip()
        home_logo = replace_logo_link(match.find("img", class_="logo-team")["src"])

        away_team = match.find("span", class_="name-team-right").text.strip()
        away_logo = replace_logo_link(match.find_all("img", class_="logo-team")[1]["src"])  

        match_date = match.find("p", class_="time-format").text.strip()
        match_link = match.find("a", class_="btn-watch")["href"]

        match_data.append({
            "home_team": home_team,
            "home_logo": home_logo,
            "away_team": away_team,
            "away_logo": away_logo,
            "match_date": match_date,
            "match_link": match_link
        })

    # Save data as a JSON file
    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(match_data, f, ensure_ascii=False, indent=4)

    print("✅ Scraping complete. Data saved to `matches.json`.")

else:
    print("❌ Failed to fetch data. Status Code:", response.status_code)
