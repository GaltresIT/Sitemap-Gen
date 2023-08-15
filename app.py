from flask import Flask, render_template, request, flash, redirect, send_file
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import validators
from datetime import datetime
from urllib.parse import urljoin, urlparse
import os
from dotenv import load_dotenv
import tempfile
import re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zipfile import ZipFile
import shutil

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Get the secret key from the environment variable

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate_sitemap', methods=['POST'])
def generate_sitemap():
    url = request.form['url']

    # Validate URL
    if not validators.url(url):
        flash('Invalid URL. Please enter a valid URL.', 'danger')
        return redirect('/')

    try:
        create_sitemap(url)
        return render_template('sitemap.html')
    except Exception as e:
        flash(f'An error occurred while generating the sitemap: {str(e)}', 'danger')
        return redirect('/')

def get_priority(url):
    # Parse the URL
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    segments = path.split('/')
    if len(segments) == 0 or (len(segments) == 1 and segments[0]):
        return '1'
    else:
        return '0.8'

def create_sitemap(url):
    # Set up the Selenium driver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    # Load the URL and wait for it to be fully loaded
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    # Find <img> tags
    images = driver.find_elements_by_tag_name('img')
    image_urls = [img.get_attribute('src') for img in images]

    # Find CSS background images
    elements_with_backgrounds = driver.find_elements_by_css_selector('[style*="background-image"]')
    for element in elements_with_backgrounds:
        style = element.get_attribute('style')
        url_match = re.search(r'background-image:\s*url\("?(.*?)"?\)', style)
        if url_match:
            image_urls.append(url_match.group(1))

    # Counter for breaking large sitemaps
    counter = 0
    sitemaps = []
    urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

    for link in driver.find_elements_by_tag_name('a'):
        href = link.get_attribute('href')
        if href and href.startswith('https'):
            try:
                last_modified_response = requests.head(href, timeout=10)
                lastmod_date = last_modified_response.headers.get('last-modified')
            except requests.RequestException:
                lastmod_date = None

            if lastmod_date is None:
                lastmod_date = datetime.utcnow().isoformat("T") + "Z"

            url_element = ET.SubElement(urlset, 'url')
            loc = ET.SubElement(url_element, 'loc')
            loc.text = urljoin(url, href)
            lastmod = ET.SubElement(url_element, 'lastmod')
            lastmod.text = lastmod_date
            changefreq = ET.SubElement(url_element, 'changefreq')
            changefreq.text = 'weekly'
            priority_value = get_priority(href)
            priority = ET.SubElement(url_element, 'priority')
            priority.text = priority_value

            for image_url in image_urls:
                image_element = ET.SubElement(url_element, 'image:image', xmlns_image="http://www.google.com/schemas/sitemap-image/1.1")
                img_loc = ET.SubElement(image_element, 'image:loc')
                img_loc.text = urljoin(url, image_url) if image_url else None

            counter += 1
            if counter >= 50000:
                sitemaps.append(urlset)
                urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
                counter = 0

    # Add videos associated with the link
    for video in link.find_elements_by_tag_name('video'):
        video_element = ET.SubElement(url_element, 'video:video', xmlns_video="http://www.google.com/schemas/sitemap-video/1.1")
        video_loc = ET.SubElement(video_element, 'video:content_loc')
        video_loc.text = video.get_attribute('src')

        thumbnail_url = video.get_attribute('data-thumbnail')  # Extract thumbnail URL from data attribute
        video_thumbnail_loc = ET.SubElement(video_element, 'video:thumbnail_loc')
        video_thumbnail_loc.text = urljoin(url, thumbnail_url) if thumbnail_url else None

        video_title_text = video.get_attribute('data-title')  # Extract video title from data attribute
        video_title = ET.SubElement(video_element, 'video:title')
        video_title.text = video_title_text if video_title_text else None

        video_description_text = video.get_attribute('data-description')  # Extract video description from data attribute
        video_description = ET.SubElement(video_element, 'video:description')
        video_description.text = video_description_text if video_description_text else None


    # Close the WebDriver
    driver.quit()

    sitemaps.append(urlset)
    temp_files = []
    for sitemap in sitemaps:
        sitemap_xml = ET.tostring(sitemap).decode('utf-8')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
        temp_file.write(sitemap_xml.encode('utf-8'))
        temp_file.close()
        temp_files.append(temp_file.name)

    # Zip multiple sitemaps if needed
    if len(temp_files) > 1:
        zip_path = tempfile.mktemp(suffix=".zip")
        with ZipFile(zip_path, 'w') as zipf:
            for temp_file in temp_files:
                zipf.write(temp_file, os.path.basename(temp_file))
                os.remove(temp_file)  # Clean up temporary file
        return [zip_path]
    else:
        return temp_files

if __name__ == '__main__':
    app.run()