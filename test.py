import requests

def search_most_popular_anime(title):
    url = 'https://graphql.anilist.co'

    query = '''
    query ($search: String, $sort: [MediaSort]) {
      Page(perPage: 5) {
        media(search: $search, type: ANIME, sort: $sort) {
          id
          title {
            romaji
            english
          }
          description(asHtml: false)
          coverImage {
            large
          }
          averageScore
          genres
          siteUrl
        }
      }
    }
    '''

    variables = {
        'search': title,
        'sort': ['POPULARITY_DESC']
    }

    response = requests.post(
        url,
        json={'query': query, 'variables': variables},
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        media_list = data.get("data", {}).get("Page", {}).get("media", [])
        if media_list:
            most_popular = media_list[0]
            print("Title:", most_popular["title"]["romaji"])
            print("English Title:", most_popular["title"]["english"])
            print("Genres:", ', '.join(most_popular["genres"]))
            print("Average Score:", most_popular["averageScore"])
            print("Description:", most_popular["description"])
            print("AniList URL:", most_popular["siteUrl"])
            print("Cover Image:", most_popular["coverImage"]["large"])
        else:
            print("No matching anime found.")
    else:
        print("Error:", response.status_code)
        print(response.text)

# Ask user for input
user_input = input("Enter anime title: ")
search_most_popular_anime(user_input)
