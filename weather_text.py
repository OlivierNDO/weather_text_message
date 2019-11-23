# Configuration
###############################################################################

# Module imports
import twilio
from twilio.rest import Client
from bs4 import BeautifulSoup as bs
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import requests
import time
import urllib

# Scraping configuration
config_ff_path = '********geckodriver.exe'
config_weather_url = 'https://**********.com/'
config_xpath_dict = {'search bar' : '//*[contains(concat( " ", @class, " " ), concat( " ", "input__inputElement__1GjGE", " " ))]',
                     'today' : '//li[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//span',
                     'temp' : '//*[contains(concat( " ", @class, " " ), concat( " ", "today_nowcard-temp", " " ))]//span',
                     'hourly button' : '//*[(@id = "looking_ahead_link")]//*[contains(concat( " ", @class, " " ), concat( " ", "cta-link", " " )) and (((count(preceding-sibling::*) + 1) = 1) and parent::*)]',
                     'temp range' : '//*[contains(concat( " ", @class, " " ), concat( " ", "closed", " " ))]//span',
                     'next 8 hours' : '//*[contains(concat( " ", @class, " " ), concat( " ", "styles__displayBtn__YPvCm", " " ))]//span[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]',
                     'hourly body' : '//tbody'}

# Twilio configuration
config_key_one = '*****************************'
config_key_two = '*****************************'
config_twilio_number = '+1**********'
config_number_dict = {'Nick' : '+1**********'}
config_send_txt_to = ['Nick']

# Define Functions
###############################################################################

def unnest_list_of_lists(LOL):
    """unnest list of lists"""
    import itertools
    return list(itertools.chain.from_iterable(LOL))

def semi_rand_intervals(min_time, max_time, n_nums):
    """random intervals of time between requests"""
    return [i for i in np.random.choice(np.linspace(min_time, max_time, 1000), n_nums)]

def semi_random_pause(min_time, max_time):
    """Pause for random amount of time between min_time and max_time"""
    time.sleep(semi_rand_intervals(min_time, max_time, 1)[0])
    
def split_list_in_chunks(my_list : list, n : int):
    """Split list <my_list> into a list of lists of size <n>"""
    return [my_list[i * n:(i + 1) * n] for i in range((len(my_list) + n - 1) // n )]  
    
def send_text(msg : str, to_numbers : list,
              from_number = config_twilio_number,
              key_one = config_key_one,
              key_two = config_key_two):
    """Send text message"""
    client = Client(key_one, key_two)
    for num in to_numbers:
        msg = client.messages.create(to = num, from_ = from_number, body = msg)
        print(msg)

def get_24hr_forecast(gecko_driver = config_ff_path, url = config_weather_url, xpath_dict = config_xpath_dict):
    """
    Use firefox and selenium to scrape local 24 hour forecast information
    
    Args:
        gecko_driver: path to firefox selenium driver on local machine
        url: initial url to visit
        xpath_dict: dictionary of xpath strings corresponding to necessary page elements
    
    Dependencies:
        pandas (import as pd)
        selenium
        time
        
    Returns:
        pandas.DataFrame
    """
    
    # Navigate to local 24-hour forecast
    driver = webdriver.Firefox(executable_path = gecko_driver)
    driver.get(url)
    semi_random_pause(2.5,4)
    today_button = driver.find_element_by_xpath(xpath_dict.get('today'))
    today_button.click()
    semi_random_pause(1,2)
    hourly = driver.find_element_by_xpath(xpath_dict.get('hourly button'))
    hourly.click()
    semi_random_pause(1,3)
    temp = driver.find_element_by_xpath(xpath_dict.get('next 8 hours'))
    temp.click()
    semi_random_pause(1,2)
    
    # Scrape and reformat hourly forecast information & close driver
    hourly_body = driver.find_element_by_xpath(xpath_dict.get('hourly body'))
    hourly_text = hourly_body.text.split('\n')
    hourly_chunks = split_list_in_chunks(hourly_text, 5)
    hourly_df = pd.DataFrame(hourly_chunks, columns = ['time', 'day', 'temp', 'precip', 'humid_wind'])
    hourly_df['time'] = [x.rjust(8,'0') for x in hourly_df['time']]
    hourly_df['temp'] = [' '.join(r.split(' ')[:-1]) for r in hourly_df['temp']]
    hourly_df['sky'] = [' '.join(r.split(' ')[:-1]) for r in hourly_df['temp']]
    hourly_df['temp'] = [r.split(' ')[-1] for r in hourly_df['temp']]
    hourly_df['humid'] = [r.split(' ')[0] for r in hourly_df['humid_wind']]
    hourly_df['wind'] = [' '.join(r.split(' ')[-2:]) for r in hourly_df['humid_wind']]
    hourly_df.drop('humid_wind', axis = 1, inplace = True)
    driver.close()
    return hourly_df

class ForecastInfo:
    """Series of functions to reformat information from the dataframe genereated by get_24_hr_forecast()"""
    def __init__(self, forecast_df):
        self.forecast_df = forecast_df
        
    def temp_func(self):
        return self.forecast_df['precip']
        
    def get_temp_range(self):
        temp_integers = [int(x[:-1]) for x in self.forecast_df['temp']]
        return 'Temperature range:                 {} - {} F'.format(str(min(temp_integers)), str(max(temp_integers)))
    
    def get_humidity_range(self):
        humid_integers = [int(x[:-1]) for x in self.forecast_df['humid']]
        return 'Humidity range:                    {}% - {}%'.format(str(min(humid_integers)), str(max(humid_integers)))
    
    def get_precip_prob(self):
        precip_integers = [int(x[:-1]) for x in self.forecast_df['precip']]
        return 'Hourly precipitation:                {}% - {}%'.format(str(min(precip_integers)), str(max(precip_integers)))
    
    def get_hourly_summary(self):
        day_time = [self.forecast_df['day'][i] + ' ' + x + ': \n' for i, x in enumerate(self.forecast_df['time'])]
        temp_precip = [self.forecast_df['temp'][i] + ', precipitation: ' + x for i, x in enumerate(self.forecast_df['precip'])]
        sky = [str(x) +'\n' for x in self.forecast_df['sky']]
        agg_summary = '\n'.join([day_time[i] + temp_precip[i] + ', ' + x for i, x in enumerate(sky)])
        return agg_summary
    
    def get_entire_text(self):
        try:
            header = '\n'.join(['Weather - next 24 hours:',
                                self.get_temp_range(),
                                self.get_precip_prob(),
                                self.get_humidity_range()])
            body = self.get_entire_text()
            txt_content = '\n\n--------------------\n\n'.join([header, body])
            return txt_content
        except:
            print('recursion error')
        

# Execute Functions
###############################################################################
if __name__ == "__main__":
    hourly_forecast = get_24hr_forecast()
    current_forecast = ForecastInfo(hourly_forecast)

    header = '\n'.join(['Weather Summary - Next 24 Hours:',
                        '-------------------------------------------',
                        current_forecast.get_temp_range(),
                        current_forecast.get_precip_prob(),
                        current_forecast.get_humidity_range()])
        
    hourly_body = '\n'.join(['Hourly Detail - Next 24 Hours:',
                             '-------------------------------------------',
                             current_forecast.get_hourly_summary()])
    
    text_msg_content = '\n\n\n'.join([header, hourly_body])
    
    send_text(msg = text_msg_content, to_numbers = [config_number_dict.get(x) for x in config_send_txt_to])
    
