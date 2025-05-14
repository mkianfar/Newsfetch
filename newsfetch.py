import os
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from collections import defaultdict
import unittest
import threading
from functools import lru_cache

class NewsAPIClient:
    def __init__(self, api_key):
        self.api_key = "75e01f0496064d5683ff5abdc0783a10"
        self.base_url = "https://newsapi.org/v2/top-headlines"

    def fetch_news(self, category="", source="", page_size=10):
        params = {
            'apiKey': self.api_key,
            'pageSize': page_size
        }
        if category:
            params['category'] = category
        if source:
            params['sources'] = source

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('articles', [])
        except requests.RequestException as e:
            print(f"Error fetching news: {e}")
            return []

class WebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    @lru_cache(maxsize=100)
    def scrape_article(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find article content
            content = soup.find('article') or soup.find('div', class_='content')
            text = content.get_text(strip=True) if content else "Content not available"
            
            # Try to find author
            author = soup.find('meta', {'name': 'author'})
            author = author['content'] if author else "Unknown"
            
            # Try to find publication date
            pub_date = soup.find('meta', {'property': 'article:published_time'})
            pub_date = pub_date['content'] if pub_date else "Unknown"
            
            return {
                'content': text[:500],  # Limit content length
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
        for article in self.articles:
            if article.get('url'):
                scraped_data = self.scraper.scrape_article(article['url'])
                article.update(scraped_data)
        self._clean_data()

    def _clean_data(self):
        # Remove duplicates based on URL
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
            # NewsAPI doesn't provide category, so we'll use source as proxy
            source = article.get('source', {}).get('name', 'Unknown')
            categories[source] += 1
        return categories

class NewsGUI:
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.root = tk.Tk()
        self.root.title("News Aggregator")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")  # Light background color
        self._setup_gui()

    def _setup_gui(self):
        # Custom font
        title_font = Font(family="Helvetica", size=16, weight="bold")
        label_font = Font(family="Helvetica", size=12)

        # Title
        title_label = tk.Label(self.root, text="News Aggregator", font=title_font, bg="#f5f5f5", fg="#333")
        title_label.pack(pady=10)

        # Input Frame
        input_frame = ttk.Frame(self.root, padding=10)
        input_frame.pack(pady=10, fill="x")

        # Category selection
        ttk.Label(input_frame, text="Category:", font=label_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.category_var = tk.StringVar()
        categories = ["", "business", "entertainment", "general", "health", "science", "sports", "technology"]
        category_combobox = ttk.Combobox(input_frame, textvariable=self.category_var, values=categories, state="readonly")
        category_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Source selection
        ttk.Label(input_frame, text="Source (optional):", font=label_font).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.source_var = tk.StringVar()
        source_entry = ttk.Entry(input_frame, textvariable=self.source_var)
        source_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Number of articles
        ttk.Label(input_frame, text="Number of Articles:", font=label_font).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.num_articles_var = tk.IntVar(value=10)
        num_articles_entry = ttk.Entry(input_frame, textvariable=self.num_articles_var)
        num_articles_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # Adjust column weights
        input_frame.columnconfigure(1, weight=1)

        # Buttons Frame
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(pady=10)

        # Fetch button
        fetch_button = ttk.Button(button_frame, text="Fetch News", command=self.fetch_news)
        fetch_button.grid(row=0, column=0, padx=10)

        # Visualize button
        visualize_button = ttk.Button(button_frame, text="Visualize Distribution", command=self.visualize)
        visualize_button.grid(row=0, column=1, padx=10)

        # Article Display Frame
        display_frame = ttk.Frame(self.root, padding=10)
        display_frame.pack(pady=10, fill="both", expand=True)

        # Article display
        self.text_area = tk.Text(display_frame, height=20, wrap="word", font=("Helvetica", 10))
        self.text_area.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Scrollbar
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

        threading.Thread(target=self._fetch_news_thread, args=(category, source, num_articles)).start()

    def _fetch_news_thread(self, category, source, num_articles):
        self.aggregator.aggregate(category, source, num_articles)
        if not self.aggregator.articles:
            messagebox.showerror("Error", "No articles found!")
            return

        for article in self.aggregator.articles:
            display_text = f"Title: {article.get('title', 'N/A')}\n"
            display_text += f"Source: {article.get('source', {}).get('name', 'N/A')}\n"
            display_text += f"Author: {article.get('author', 'N/A')}\n"
            display_text += f"Publication Date: {article.get('publication_date', 'N/A')}\n"
            display_text += f"Content: {article.get('content', '')[:100]}...\n"
            display_text += "-" * 50 + "\n"
            self.text_area.insert(tk.END, display_text)

    def visualize(self):
        distribution = self.aggregator.get_category_distribution()
        if not distribution:
            messagebox.showerror("Error", "No data to visualize!")
            return

        plt.figure(figsize=(10, 6))
        plt.bar(distribution.keys(), distribution.values(), color="#4CAF50")
        plt.xticks(rotation=45)
        plt.xlabel("Sources")
        plt.ylabel("Number of Articles")
        plt.title("Distribution of News Articles by Source")
        plt.tight_layout()
        plt.show()

    def run(self):
        self.root.mainloop()

class TestNewsAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = NewsAggregator("YOUR_API_KEY")  # Replace with actual API key

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
    # Replace with your actual News API key
    API_KEY = os.getenv("NEWS_API_KEY", "YOUR_API_KEY")
    
    aggregator = NewsAggregator(API_KEY)
    gui = NewsGUI(aggregator)
    gui.run()

    # Run unit tests
    # unittest.main(argv=[''], exit=False)
