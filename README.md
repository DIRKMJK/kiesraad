The Dutch election council publishes election results in two formats: 

- A website [Verkiezingsuitslagen][uitslagen] where for each election, each municipality has its own page with local results;
- Files in Election Markup Language (EML), published at the national government’s [data portal][portal].

[Background][background] (in Dutch)

# Prerequisites
You will need to have Python 3 installed, and the following libraries:
```sh
pip3 install pandas xmltodict selenium bs4
```

# Scrape Verkiezingsuitslagen website

This will produce a csv file containing results per municipality.

Example:

```python
from kiesraad import scrape

scrape.scrape('TK20170315')
df = scrape.parse_downloaded_pages('TK20170315')
```

If you want to extract seats instead of votes:

```python
df = scrape.parse_downloaded_pages('TK20170315', unit='seats')
```


# Parse EML files

This will produce csv files for each municipality, containing results at polling station level. If desired, these can include votes per candidate. Note that you’ll first need to download the EML files from the government’s [data portal][portal].

Example:

```python
from pathlib import Path
from kiesraad import parse_eml

source = Path('../data/TK2017')
dfs = parse_eml.parse_eml(source)
target = source / 'csv'
target.mkdir(exist_ok=True)
for name, df in dfs.items():
    path = target / f'{name}.csv'
    df.to_csv(path, index=False)
```

# Caveat

Please check the results; they are not guaranteed to be accurate. 



[scrape]:https://dirkmjk.nl/en/2018/05/how-use-python-and-selenium-scraping-election-results
[eml]:https://dirkmjk.nl/en/2018/07/converting-election-markup-language-eml-csv
[portal]:https://data.overheid.nl/community/organization/kiesraad
[uitslagen]:https://www.verkiezingsuitslagen.nl/
[background]:https://dirkmjk.nl/p/verkiezingskaart/
