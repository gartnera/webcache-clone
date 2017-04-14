#!/usr/bin/env python3

import argparse
import requests
from lxml import html
from tld import get_tld
from urllib.parse import urlparse, parse_qs
import os
import re

headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
}

def strip_scheme(url):
    url = url.replace('https://', '')
    url = url.replace('http://', '')
    return url

def expand_index(url):
    if url == '' or url == '/':
        return '/index.html'
    else:
        return url

def handle_url(url, rootDomain, processSubdomains, urlBase):
    #prevent circular requests
    if (os.path.exists(url)):
        return
    r = requests.get(urlBase + url, headers=headers)
    handle_page(r, rootDomain, processSubdomains, urlBase)

def handle_page(page, rootDomain, processSubdomains, urlBase):
    if page.status_code != 200:
        print('Unable to retrieve {}'.format(page.url))
        return

    #extract actual url from webcache url
    url = urlparse(page.url)
    url = parse_qs(url.query)['q'][0].replace('cache:', '')
    url = urlparse(url)
    domain = url.netloc

    path = expand_index(url.path)

    tree = html.fromstring(page.content)

    #cleanup
    el = tree.cssselect('#google-cache-hdr')[0]
    el.getparent().remove(el)

    #write out
    path = domain + path
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    f = open(path, "wb")
    f.write(html.tostring(tree))

    print('{} -> {}'.format(url.geturl(), path))

    #process links
    links = tree.cssselect('a')
    for link in links:
        href = link.get('href')

        if not re.match('^(https?:)?//', href) and ('/' in href or '.html' in href):
            if href[0] != '/':
                href = '/' + href
            href = domain + href
        elif processSubdomains and rootDomain in href:
            href = strip_scheme(href)
        elif domain in href:
            href = strip_scheme(href)
        else:
            continue

        handle_url(href, rootDomain, processSubdomains, urlBase)

parser = argparse.ArgumentParser(description='Clone a website from google cache')
parser.add_argument('domain', help='The domain to clone (without http)')
parser.add_argument('-s', '--subdomains', help='Clone subdomains', action='store_true')

args = parser.parse_args()

urlBase = 'https://webcache.googleusercontent.com/search?q=cache:'

#use http or https?
scheme = 'http://'
url = urlBase + scheme + args.domain

r = requests.get(url, headers=headers, allow_redirects=False)

if r.status_code == 302:
    print(r.content)
    print("Capcha detected, please navigate to {} to continue".format(url))
    exit(-1)

if r.status_code != 200:
    scheme = 'https://'
    url = urlBase + scheme + args.domain
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("Domain invalid")
        exit(-2)

print('Scheme detected as {}'.format(scheme))

domain = args.domain

if args.subdomains:
    domain = get_tld(scheme + domain)

handle_page(r, domain, args.subdomains, urlBase+scheme)

