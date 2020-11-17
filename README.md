# Goodreads Reviews Scraper

Command line utility for fetching a given user's reviews from Goodreads and writing them to a csv file.

## Usage
```
$ python scraper.py --email={login_email} --password={login_password} \
    --target_user_id={user_id_for_review_author}
```

- email: Email address for logging into Goodreads
- password: Password for logging into Goodreads
- target_user_id: User ID whose reviews you want to fetch