The Dutch election council publishes election results in two formats: 

- A website [Verkiezingsuitslagen][uitslagen] where for each election, each municipality has its own page with local results;
- Files in Election Markup Language (EML), published at the national government’s [data portal][portal].

# Scrape Verkiezingsuitslagen website

This will produce a csv file containing results per municipality.

Example:

<codeblock>
from kiesraad import scrape

scrape.scrape('TK20170315')
df = scrape.parse_downloaded_pages('TK20170315')
</codeblock>


# Parse EML files

This will produce csv files for each municipality, containing results at polling station level. If desired, these can include votes per candidate.

Example:

<codeblock>
from pathlib import Path
import pandas as pd
from kiesraad import parse_eml

source = Path('../data/TK2017')
dfs = parse_eml.parse_eml(source)
target = source / 'csv'
target.mkdir(exist_ok=True)
for name, df in dfs.items():
    path = target / f'{name}.csv'
    df.to_csv(path, index=False)
</codeblock>

# Caveat

Please check the results; they are not guaranteed to be accurate. 



[scrape]:https://dirkmjk.nl/en/2018/05/how-use-python-and-selenium-scraping-election-results
[eml]:https://dirkmjk.nl/en/2018/07/converting-election-markup-language-eml-csv
[portal]:https://data.overheid.nl/data/dataset?maintainer_facet=http%3A%2F%2Fstandaarden.overheid.nl%2Fowms%2Fterms%2FKiesraad
[uitslagen]:https://www.verkiezingsuitslagen.nl/