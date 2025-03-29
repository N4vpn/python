import requests
from bs4 import BeautifulSoup

def replace_logo_link(logo_url):
    if logo_url == 'https://image.azencode.com/teams/40.png':
        return 'https://football.redsport.live//storage/01HQNMEPGZC4XHY6ZWW022VAYN.png'
    return logo_url

api_url = "https://aesport.tv/?s_key=Liverpool"

response = requests.get(api_url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    matches = soup.find_all("div", class_="row-item-match")
    match_data = []
    for match in matches:
        home_team = match.find("span", class_="name-team-left").text.strip()
        home_logo = match.find("img", class_="logo-team")["src"]
        home_logo = replace_logo_link(home_logo)

        away_team = match.find("span", class_="name-team-right").text.strip()
        away_logo = match.find_all("img", class_="logo-team")[1]["src"]
        away_logo = replace_logo_link(away_logo)

        match_date = match.find("p", class_="time-format").text.strip()

        match_data.append({
            "match_date": match_date,
            'home_team': {
               'name': home_team,
               'logo_url': home_logo
            },
            'away_team': {
               'name': away_team,
               'logo_url': away_logo
            }
        })

    for match in match_data:
        print(match)

else:
    print("Failed to fetch data. Status Code:", response.status_code)
