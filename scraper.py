"""
Command line utility for fetching a given user's reviews from Goodreads.
Writes reviews to CSV file.

Params:
    - email: Email address for logging into Goodreads
    - password: Password for logging into Goodreads
    - target_user_id: User ID whose reviews you want to fetch

Usage:
    $ python scraper.py --email={login_email} --password={login_password} \
        --target_user_id={user_id_for_review_author}
"""
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from csv import DictWriter
from datetime import datetime
import requests

LOGIN_URL = "https://www.goodreads.com/user/sign_in"
REVIEW_URL = "https://www.goodreads.com/review/show/{}"
REVIEW_LIST_URL = "https://www.goodreads.com/review/list/{}?view=reviews&shelf=read&page={}" 


def get_authenticity_token(html):
    soup = BeautifulSoup(html, "html.parser")
    token = soup.find('input', attrs={'name': 'authenticity_token'})
    if not token:
        print('could not find `authenticity_token` on login form')
    return token.get('value').strip()


def get_login_n(html):
    # there is a hidden input named `n` that also needs to be passed
    soup = BeautifulSoup(html, "html.parser")
    n = soup.find('input', attrs={'name': 'n'})
    if not n:
        print('could not find `n` on login form')
    return n.get('value').strip()


def get_max_page_num(html):
    soup = BeautifulSoup(html, "html.parser")
    max_page_num = soup.find('div', id='reviewPagination').find_all('a', class_=None)[-1].text
    if not max_page_num:
        return 0
    return int(max_page_num)


def parse_review_list(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all('tr', class_='review')
    return [row.get('id').replace('review_', '') for row in rows]


def parse_review(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find('a', class_='bookTitle').get_text()
    author = soup.find('a', class_='authorName').get_text()
    rating = soup.find('meta', itemprop='ratingValue').get('content')
    text = soup.find('div', class_='reviewText')
    timeline = soup.find_all('div', class_='readingTimeline__text')

    review_date = soup.find('span', itemprop='datePublished').get_text()
    if review_date:
        review_date = datetime.strptime(review_date.strip(), '%b %d, %Y').strftime('%Y-%m-%d')
    else:
        review_date = None

    for div in timeline[::-1]:
        if div.get_text():
            date, _, context = div.get_text().strip().partition('\n')

        if 'Finished Reading' in context:
            last_finished_date = datetime.strptime(date.strip().replace('  ', ' 0'), '%B %d, %Y').strftime('%Y-%m-%d')
            break
        else:
            last_finished_date = None
    return {
        'title': title.strip() if title else None,
        'author': author.strip() if author else None,
        'review_date': review_date,
        'last_finished_date':  last_finished_date,
        'rating': int(rating) if rating else None,
        'text': text.get_text().strip() if text else None
    }


def main(email, password, target_user_id):
    payload = {
        'user[email]': email,
        'user[password]': password,
        'utf8': '&#x2713;',
    }

    session = requests.Session()
    outfile = open('reviews.csv', mode='w')
    writer = DictWriter(outfile, fieldnames=[
        'review_id', 'title', 'author', 'review_date', 'last_finished_date', 'rating', 'text'
    ])

    session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'}
    response = session.get(LOGIN_URL)

    token = get_authenticity_token(response.text)
    n = get_login_n(response.text)
    payload.update({
        'authenticity_token': token,
        'n': n
    })

    print(f"attempting to log in as {email}")
    p = session.post(LOGIN_URL, data=payload)

    page_num = 1
    max_page_num = 1  # assume 1 page and then get max page number later
    review_ids = set()
    
    while page_num <= max_page_num:
        print(f"parsing reviews list number {page_num} of {max_page_num}")
        response = session.get(REVIEW_LIST_URL.format(target_user_id, page_num))

        if max_page_num == 1:
            max_page_num = get_max_page_num(response.text)

        for id in parse_review_list(response.text):
            print("parsing review id {}: {}".format(id, REVIEW_URL.format(id)))
            review_ids.add(id)

            response = session.get(REVIEW_URL.format(id))
            r = parse_review(response.text)
            r['review_id'] = id
            writer.writerow(r)

        page_num += 1

    session.close()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--email', type=str)
    parser.add_argument('--password', type=str)
    parser.add_argument('--target_user_id', type=str)
    args = parser.parse_args()
    main(args.email, args.password, args.target_user_id)