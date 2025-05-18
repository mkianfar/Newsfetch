import os
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
from datetime import datetime
import matplotlib.ticker as ticker
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from collections import defaultdict
import unittest
import threading
from functools import lru_cache
import re

class NewsAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/top-headlines"

    def fetch_news(self, category="", source="", page_size=10, country="us"):
        params = {
            'apiKey': self.api_key,
            'pageSize': page_size
        }
        if source:
            params['sources'] = source
        elif category:
            params['category'] = category
            params['country'] = country
        else:
            params['country'] = country

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "ok":
                print(f"API Error: {data.get('message', 'Unknown error')}")
                return []
            return data.get('articles', [])
        except requests.RequestException as e:
            print(f"Error fetching news: {e}")
            return []

class WebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': (
                # Use a more realistic, up-to-date browser user agent
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
        }

    @lru_cache(maxsize=100)
    def scrape_article(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 403:
                print(f"Access denied (403) for url: {url}")
                return {'content': '', 'author': 'Unknown', 'publication_date': 'Unknown'}
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            content = soup.find('article') or soup.find('div', class_='content')
            text = content.get_text(strip=True) if content else ""

            author = soup.find('meta', {'name': 'author'})
            author = author['content'] if author else "Unknown"

            pub_date = soup.find('meta', {'property': 'article:published_time'})
            pub_date = pub_date['content'] if pub_date else "Unknown"

            return {
                'content': text[:500] if text else "",
                'author': author,
                'publication_date': pub_date
            }
        except (requests.RequestException, AttributeError) as e:
            print(f"Error scraping article: {e}")
            return {'content': '', 'author': 'Unknown', 'publication_date': 'Unknown'}

class NewsAggregator:
    def __init__(self, api_key):
        self.api_client = NewsAPIClient(api_key)
        self.scraper = WebScraper()
        self.articles = []

    def aggregate(self, category="", source="", page_size=10):
        self.articles = self.api_client.fetch_news(category, source, page_size)
        print(f"[DEBUG] Fetched {len(self.articles)} articles")
        for article in self.articles:
            if article.get('url'):
                scraped_data = self.scraper.scrape_article(article['url'])
                if not scraped_data.get("content"):
                    scraped_data["content"] = article.get("description") or article.get("content") or "Content not available"
                article.update(scraped_data)
        self._clean_data()

    def _clean_data(self):
        seen_urls = set()
        unique_articles = []
        for article in self.articles:
            if article.get('url') and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        self.articles = unique_articles

    def get_category_distribution(self):
        categories = defaultdict(int)
        for article in self.articles:
            source = article.get('source', {}).get('name', 'Unknown')
            categories[source] += 1
        return categories

class NewsGUI:
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.root = tk.Tk()
        self.root.title("News Aggregator")
        self.root.geometry("900x700")
        self.root.configure(bg="#f3f6fd")  # Windows 11 light background

        # Use ttk theme for modern look
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f6fd")
        style.configure("TLabel", background="#f3f6fd", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11), padding=6)
        style.configure("TEntry", font=("Segoe UI", 11))
        style.configure("TCombobox", font=("Segoe UI", 11))
        style.configure("TProgressbar", thickness=8, troughcolor="#e3eafc", background="#0078D7", bordercolor="#e3eafc", lightcolor="#e3eafc", darkcolor="#0078D7")

        # Remove progress bar, add loading label
        self.loading_label = tk.Label(self.root, text="", font=("Segoe UI", 12), bg="#f3f6fd", fg="#0078D7")
        self.loading_label.pack(pady=(5, 0))

        self._setup_gui()

    def _setup_gui(self):
        title_font = Font(family="Segoe UI", size=20, weight="bold")
        label_font = Font(family="Segoe UI", size=12)

        title_label = tk.Label(self.root, text="📰 News Aggregator", font=title_font, bg="#f3f6fd", fg="#222")
        title_label.pack(pady=(20, 10))

        input_frame = ttk.Frame(self.root, padding=20, style="TFrame")
        input_frame.pack(pady=10, fill="x")

        ttk.Label(input_frame, text="Category:", font=label_font, style="TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.category_var = tk.StringVar()
        categories = ["", "Business", "Entertainment", "General", "Health", "Science", "Sports", "Technology"]
        category_combobox = ttk.Combobox(input_frame, textvariable=self.category_var, values=categories, state="readonly", font=("Segoe UI", 11))
        category_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(input_frame, text="Source (optional):", font=label_font, style="TLabel").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.source_var = tk.StringVar()
        source_entry = ttk.Entry(input_frame, textvariable=self.source_var, font=("Segoe UI", 11))
        source_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(input_frame, text="Number of Articles:", font=label_font, style="TLabel").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.num_articles_var = tk.IntVar(value=10)
        num_articles_entry = ttk.Entry(input_frame, textvariable=self.num_articles_var, font=("Segoe UI", 11))
        num_articles_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        input_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self.root, padding=10, style="TFrame")
        button_frame.pack(pady=10)

        self.fetch_button = ttk.Button(button_frame, text="Fetch News", command=self.fetch_news, style="TButton")
        self.fetch_button.grid(row=0, column=0, padx=10)

        self.visualize_button = ttk.Button(button_frame, text="Visualize Distribution", command=self.visualize, style="TButton")
        self.visualize_button.grid(row=0, column=1, padx=10)

        display_frame = ttk.Frame(self.root, padding=10, style="TFrame")
        display_frame.pack(pady=10, fill="both", expand=True)

        self.text_area = tk.Text(display_frame, height=20, wrap="word", font=("Segoe UI", 11), bg="#f8fafc", fg="#222", relief="flat", bd=0, highlightthickness=1, highlightbackground="#e3eafc")
        self.text_area.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(display_frame, command=self.text_area.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_area.configure(yscrollcommand=scrollbar.set)

    def fetch_news(self):
        self.text_area.delete(1.0, tk.END)
        category = self.category_var.get()
        source = self.source_var.get()
        num_articles = self.num_articles_var.get()

        if not category and not source:
            messagebox.showerror("Error", "Please select a category or provide a source.")
            return

        # Disable buttons while fetching
        self.fetch_button.config(state="disabled")
        self.visualize_button.config(state="disabled")

        # Show loading text
        self.loading_label.config(text="Loading...")
        self.root.update()

        # Start the thread as a daemon
        threading.Thread(target=self._fetch_news_thread, args=(category, source, num_articles), daemon=True).start()

    def _ordinal(self, n):
        # Returns ordinal string for a given integer (e.g., 1 -> 1st)
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def _extract_author_and_date(self, text):
        # Try to extract author (e.g., By John Doe) and date (e.g., May 17, 2025)
        author = None
        date_str = None

        # Improved author extraction: match "By" followed by a name, but stop at the first uppercase letter not preceded by a space (e.g., "BySam QuinnMay" -> "Sam Quinn")
        author_match = re.search(r'By([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)', text)
        if author_match:
            name = author_match.group(1)
            # Scan through the name and stop at the first uppercase letter not after a space
            result = []
            prev_char = ' '
            for i, c in enumerate(name):
                if c.isupper() and prev_char != ' ' and i != 0:
                    break
                result.append(c)
                prev_char = c
            # Remove any trailing whitespace and extra spaces
            author = ' '.join(''.join(result).split())

        # Date: look for Month Day, Year (e.g., May 17, 2025)
        date_match = re.search(r'([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})', text)
        if date_match:
            try:
                dt = datetime.strptime(' '.join(date_match.groups()), "%B %d %Y")
                day = self._ordinal(dt.day)
                date_str = dt.strftime(f"{day} %B, %Y")
            except Exception:
                date_str = None

        return author, date_str

    def _fetch_news_thread(self, category, source, num_articles):
        self.aggregator.aggregate(category, source, num_articles)
        if not self.aggregator.articles:
            self.root.after(0, lambda: messagebox.showerror("Error", "No articles found!"))
            self.root.after(0, self._hide_loading)
            self.root.after(0, self._enable_buttons)
            return

        for article in self.aggregator.articles:
            # Try to get author and date from scraped data
            author = article.get('author', 'Unknown')
            raw_date = article.get('publication_date', 'Unknown')
            content = article.get('content', '')

            # If author or date is unknown, try to extract from content
            if author == "Unknown" or raw_date == "Unknown":
                extracted_author, extracted_date = self._extract_author_and_date(content)
                if author == "Unknown" and extracted_author:
                    author = extracted_author
                if raw_date == "Unknown" and extracted_date:
                    formatted_date = extracted_date
                else:
                    # fallback to old logic for date
                    if raw_date != 'Unknown':
                        try:
                            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                            day = self._ordinal(dt.day)
                            formatted_date = dt.strftime(f'{day} %B, %Y')
                        except ValueError:
                            formatted_date = raw_date
                    else:
                        formatted_date = 'Unknown'
            else:
                # Use the scraped date if available
                try:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    day = self._ordinal(dt.day)
                    formatted_date = dt.strftime(f'{day} %B, %Y')
                except ValueError:
                    formatted_date = raw_date

            display_text = (
                f"{'='*80}\n"
                f"📰 Title: {article.get('title', 'N/A')}\n"
                f"📢 Source: {article.get('source', {}).get('name', 'N/A')}\n"
                f"✍️ Author: {author}\n"
                f"📅 Published: {formatted_date}\n\n"
                f"{content[:300]}...\n"
                f"{'='*80}\n\n"
            )
            self.root.after(0, lambda text=display_text: self.text_area.insert(tk.END, text))

        self.root.after(0, self._hide_loading)
        self.root.after(0, self._enable_buttons)

    def _hide_loading(self):
        self.loading_label.config(text="")
        self.root.update()

    def _enable_buttons(self):
        self.fetch_button.config(state="normal")
        self.visualize_button.config(state="normal")

    def visualize(self):
        distribution = self.aggregator.get_category_distribution()
        if not distribution:
            messagebox.showerror("Error", "No data to visualize!")
            return

        plt.figure(figsize=(10, 6))
        plt.bar(distribution.keys(), distribution.values(), color="#0078D7")
        plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.xticks(rotation=45)
        plt.xlabel("Sources")
        plt.ylabel("Number of Articles")
        plt.title("Distribution of News Articles by Source")
        plt.tight_layout()
        plt.show()

    def run(self):
        self.root.mainloop()

# For unit testing (optional)
class TestNewsAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = NewsAggregator("75e01f0496064d5683ff5abdc0783a10")

    def test_api_fetch(self):
        articles = self.aggregator.api_client.fetch_news(category="technology")
        self.assertIsInstance(articles, list)

    def test_scraper(self):
        scraper = WebScraper()
        result = scraper.scrape_article("https://www.example.com")
        self.assertIsInstance(result, dict)
        self.assertIn('content', result)
        self.assertIn('author', result)

    def test_data_cleaning(self):
        self.aggregator.articles = [
            {'url': 'test1', 'title': 'Test'},
            {'url': 'test1', 'title': 'Test'},
            {'url': 'test2', 'title': 'Test2'}
        ]
        self.aggregator._clean_data()
        self.assertEqual(len(self.aggregator.articles), 2)

if __name__ == "__main__":
    API_KEY = os.getenv("NEWS_API_KEY", "75e01f0496064d5683ff5abdc0783a10")
    aggregator = NewsAggregator(API_KEY)
    gui = NewsGUI(aggregator)
    gui.run()
