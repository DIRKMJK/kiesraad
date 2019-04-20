"""Download Dutch election results per municipality"""

import time
import re
import shutil
from pathlib import Path, PosixPath
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup as bs

XPATH_PROVINCES = '//*[@id="search"]/div/div[1]/div'
XPATH_CITIES = '//*[@id="search"]/div/div[2]/div'
DATA_FOLDER = Path('../data/')


def string_to_int(string):

    """Convert string to int

    :param str string: String to convert to int
    :rtype: str

    """

    string = string.replace('.', '')
    string = string.split('(')[0].strip()
    return int(string)


def count_options(xpath, browser, max_tries):

    """Count the number of options of an element selected by its xpath

    :param xpath: Xpath of the element
    :param browser: Selenium browser element
    :param max_tries: Maximum number of tries before giving up
    :return: number of tries
    :rtype: int

    """

    time.sleep(3)
    tries = 0
    while tries < max_tries:

        try:
            element = browser.find_element_by_xpath(xpath)
            count = len(element.find_elements_by_tag_name('option'))
            if count > 1:
                return count
        except NoSuchElementException:
            pass

        time.sleep(1)
        tries += 1
    return count


def click_option(xpath, i, browser, max_tries):

    """Return text of i-th option of an element

    :param xpath: Xpath of the element
    :param i: Index of the option to be clicked
    :param browser: Selenium browser object
    :param max_tries: Maximum number of tries before giving up
    :return: text of the i-th option, or None if failed
    :rtype: str

    """

    tries = 0
    while tries < max_tries:
        try:
            element = browser.find_element_by_xpath(xpath)
            options = element.find_elements_by_tag_name('option')
            options[i].click()
            return options[i].text
        except:
            time.sleep(1)
            tries += 1
    return None


def write_to_file(browser, province, city, folder, max_tries):

    """Check if page is loaded and write html to file

    :param browser: Selenium browser object
    :param province: Province the city is part of
    :param city: Name of the municipality
    :param folder: Location where file must be stored
    :param max_tries: Maximum number of tries before giving up

    """

    loading = True
    count = 0
    while loading:
        html = browser.page_source
        if '<h3>{}</h3>'.format(city) in html:
            loading = False
        else:
            time.sleep(0.5)
            count += 1
        if count > max_tries:
            print('FAILED TO LOAD', province, city)
            break
    city_cleaned = re.sub(r'[^a-zA-Z\s]', '', city)
    path = folder / '{}.html'.format(city_cleaned)
    path.write_text(html)


def scrape(election, url=None, data_folder=DATA_FOLDER, max_tries=15):

    """Store the html pages of election results by city

    :param election: Last part of the url of the landing page for the election
        at verkiezingsuitslagen.nl, e.g. 'TK20170315'.
    :param url: Url of landing page for election (optional)
    :param data_folder: Folder where html files are stored
    :param max_tries: Maximum number of tries before giving up

    """

    if url is None:
        url = f'https://www.verkiezingsuitslagen.nl/verkiezingen/detail/{election}'
    if not isinstance(data_folder, PosixPath):
        data_folder = Path(data_folder)
    browser = webdriver.Chrome()
    browser.get(url)
    city = None
    nr_provinces = count_options(XPATH_PROVINCES, browser, max_tries)
    for i_1 in range(1, nr_provinces):
        province = click_option(XPATH_PROVINCES, i_1, browser, max_tries)
        print(province)
        nr_cities = count_options(XPATH_CITIES, browser, max_tries)
        if nr_cities == 1:
            print('NO CITIES FOR', election, province, max_tries)
        else:
            for i_2 in range(1, nr_cities):
                city = click_option(XPATH_CITIES, i_2, browser, max_tries)
                folder = data_folder / election / province
                folder.mkdir(parents=True, exist_ok=True)
                if city is not None:
                    write_to_file(browser, province, city, folder, max_tries)
    browser.close()


def parse_downloaded_pages(election, data_folder=DATA_FOLDER,
                           remove_html=True, unit='votes'):

    """Parse html files

    :param election: Last part of the url of the landing page for the election
        at verkiezingsuitslagen.nl, e.g. 'TK20170315'
    :param data_folder: Folder where html files are stored
    :param remove_html: If True, html pages will be removed after parsing
    :return: pandas DataFrame containing the election results
    :rtype: pandas.core.frame.DataFrame

    """

    if unit not in ['votes', 'seats']:
        raise ValueError('unit must be votes or seats')
    data = []
    if not isinstance(data_folder, PosixPath):
        data_folder = Path(data_folder)
    folder = data_folder / election
    for path in folder.glob('**/*.html'):
        item = {}
        parts = path.parts
        item['Verkiezing'] = parts[2]
        item['Provincie'] = parts[3]
        html = path.read_text()
        soup = bs(html, 'lxml')
        item['Gemeente'] = soup.findAll('h3')[-1].text
        algemeen = soup.find('ul', {'id': 'algemeneUitslagen'})
        values = algemeen.findAll('span', class_='value')
        values = [string_to_int(v.text) for v in values]
        (item['Kiesgerechtigden'], item['Opkomst'],
         item['Blanco'], item['Ongeldig']) = values
        divs = [d for d in soup.findAll('div') if 'partij-naam' in str(d)]
        for div in divs:
            partij = div.find('h4', class_='partij-naam').text
            if unit == 'votes':
                value = div.find('span', class_='value').text
            else:
                values = div.findAll('span', class_='value')
                if len(values) > 1:
                    value = values[-1].text
                else:
                    value = '0'
            item[partij] = string_to_int(value)
        data.append(item)
    df = pd.DataFrame(data)
    first = ['Verkiezing', 'Provincie', 'Gemeente',
             'Kiesgerechtigden', 'Opkomst', 'Blanco', 'Ongeldig']
    last = [c for c in df.columns if c not in first]
    df = df[first + last]
    df.sort_values(by='Gemeente', inplace=True)
    df.reset_index(drop=True, inplace=True)
    if remove_html:
        shutil.rmtree(folder)
    return df
