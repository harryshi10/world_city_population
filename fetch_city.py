import pandas as pd
from urlparse import urljoin
from requests import get
from bs4 import BeautifulSoup
import re
import logging
import json

CITY_LIST_FILE = "./city_list.txt"
OUTPUT_FILE = "./city_output.csv"


def get_class_list(url, for_what):
    raw_data = get(url)
    soup = BeautifulSoup(raw_data.text, 'html.parser')
    if for_what == "pop":
        class_list = soup.findAll(True, {"class": ["mergedtoprow", "mergedrow"]})
        return class_list
    elif for_what == "cord":
        script_list = soup.find_all("script")
        return script_list


def get_lat_lon(class_list):
    for body in class_list:
        if "wgCoordinates" in body.text:        # find cord body
            cord_str = body.text.split('"wgCoordinates":{')[1].split('}')[0]       # get lat:xxx, long:xxx
            cord_str = '{' + cord_str + '}'     # to json format
            lat, lon = json.loads(cord_str)["lat"], json.loads(cord_str)["lon"]
            return lat, lon
    raise Exception("no wgCoordinates tag on web")


def get_numbers_in_body(body):
    pop = body.find("td")
    pop = [int(x) for x in re.findall("\d+", str(pop).replace(",", "").replace(".", ""))]
    return max(pop) if len(pop)!=0 else 0


def get_pop(class_list):
    pop_list = []
    lenth = len(class_list)
    for index in range(lenth):
        if "Population" in str(class_list[index].find("th")):
            for i in range(1, 4):       # pop = max(index+1, index+2, index+3)
                if index+i == lenth:
                    break
                else:
                    pop = get_numbers_in_body(class_list[index + i])
                    pop_list.append(pop)
            return max(pop_list)
    raise Exception("no Population tag on the web")


def get_country_name_and_pop(class_list):
    for body in class_list:
        if "Country" in str(body.find("th")):
            country_body_list = body.find_all("a")
            if len(country_body_list) != 0:         # have a label
                for country_body in country_body_list:
                    country_name = country_body.get("title")
                    if ("state" not in country_name) and ("Country" not in country_name):       # country_name is ok
                        break
                url = country_body.get("href")
                url = urljoin("https://en.wikipedia.org/wiki/", url)
            else:
                country_str = str(body.find("td"))
                country_name = country_str[country_str.index(">")+1: country_str.index("<", 1)]           # fetch country from <td>China</td>
                url = "https://en.wikipedia.org/wiki/{}".format(country_name)
            class_list_country = get_class_list(url, "pop")
            country_pop = get_pop(class_list_country)
            return country_name, country_pop
    raise Exception("no Country tag on the web")


if __name__ == "__main__":
    result = []
    df = pd.read_csv(CITY_LIST_FILE, header=None)
    cities = df[0].tolist()
    for city in cities:
        try:
            city_replace = re.search("\w+", city).group() if "city" in city else city     # "xxx city" to "xxx"
            url = "https://en.wikipedia.org/wiki/{}".format(city_replace)
            class_list = get_class_list(url, "pop")
            city_pop = get_pop(class_list)
        except Exception as e:  # city warning
            logging.warning("{} happens in {}".format(e, city))
            city_pop = None
        try:
            script_list = get_class_list(url, "cord")
            lat, lon = get_lat_lon(script_list)
        except Exception as e:
            lat, lon = None, None
            logging.warning("{} happens in {}".format(e, city))
        try:
            country_name, country_pop = get_country_name_and_pop(class_list)
        except Exception as e:      # country warning
            logging.warning("{} happens in the country of {}".format(e, city))
            country_name, country_pop = None, None
        result.append((city, city_pop, lat, lon, country_name, country_pop))
    df = pd.DataFrame(result, columns=["city", "city_pop", "lat", "lon", "country", "country_pop"])
    df.to_csv(OUTPUT_FILE, index=False)



