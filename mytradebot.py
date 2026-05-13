import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv
import os
import alpaca_trade_api as tradeapi
from openai import OpenAI

load_dotenv()

# নিরাপ Secure keys
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
OPENAI_KEY = os.getenv("OPENAI_KEY")

BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, BASE_URL, api_version="v2")
client = OpenAI(api_key=OPENAI_KEY)

DATA_FILE = "equities.json"


def fetch_portfolio():
    try:
        positions = api.list_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "unrealized_pl": float(p.unrealized_pl),
            }
            for p in positions
        ]
    except Exception as e:
        return []


def fetch_open_orders():
    try:
        orders = api.list_orders(status="open")
        return [
            {
                "symbol": o.symbol,
                "qty": float(o.qty),
                "limit_price": float(o.limit_price) if o.limit_price else None,
                "side": o.side,
            }
            for o in orders
        ]
    except Exception:
        return []
def analyze_portfolio(message):
    portfolio = fetch_portfolio()
    orders = fetch_open_orders()

    prompt = f"""
    You are an AI portfolio manager.

    Portfolio:
    {portfolio}

    Open Orders:
    {orders}

    Question: {message}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"
def get_latest_price(symbol):
    try:
        trade = api.get_latest_trade(symbol)
        return float(trade.price)
    except Exception:
        return None


def place_limit_order(symbol, price):
    try:
        api.submit_order(
            symbol=symbol,
            qty=1,
            side="buy",
            type="limit",
            time_in_force="gtc",
            limit_price=price,
        )
        return True
    except Exception as e:
        print("Order error:", e)
        return False
class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Trading Bot")

        self.equities = self.load_equities()
        self.running = True

        self.build_ui()
        self.refresh_table()

        threading.Thread(target=self.auto_update, daemon=True).start()

    def build_ui(self):
        frame = tk.Frame(self.root)
        frame.pack()

        self.symbol_entry = tk.Entry(frame)
        self.symbol_entry.grid(row=0, column=0)

        self.levels_entry = tk.Entry(frame)
        self.levels_entry.grid(row=0, column=1)

        self.drawdown_entry = tk.Entry(frame)
        self.drawdown_entry.grid(row=0, column=2)

        tk.Button(frame, text="Add", command=self.add_equity).grid(row=0, column=3)

        self.tree = ttk.Treeview(self.root, columns=("Symbol", "Entry", "Status"), show="headings")
        for col in ["Symbol", "Entry", "Status"]:
            self.tree.heading(col, text=col)
        self.tree.pack()
        self.chat_input = tk.Entry(self.root, width=50)
        self.chat_input.pack()

        tk.Button(self.root, text="Ask AI", command=self.ask_ai).pack()

        self.chat_output = tk.Text(self.root, height=8)
        self.chat_output.pack()

    def add_equity(self):
        symbol = self.symbol_entry.get().upper()
        levels = int(self.levels_entry.get())
        drawdown = float(self.drawdown_entry.get()) / 100

        price = get_latest_price(symbol)
        if not price:
            messagebox.showerror("Error", "Invalid symbol")
            return

        self.equities[symbol] = {
            "entry_price": price,
            "levels": levels,
            "drawdown": drawdown,
            "status": "ON",
        }

        self.save_equities()
        self.refresh_table()

    def trade_logic(self):
        for symbol, data in self.equities.items():
            if data["status"] != "ON":
                continue

            price = get_latest_price(symbol)
            if not price:
                continue

            target = data["entry_price"] * (1 - data["drawdown"])

            if price <= target:
                place_limit_order(symbol, price)

    def auto_update(self):
        while self.running:
            time.sleep(5)
            self.trade_logic()

    def ask_ai(self):
        msg = self.chat_input.get()
        if not msg:
            return

        response = analyze_portfolio(msg)

        self.chat_output.insert(tk.END, f"\nYou: {msg}\n{response}\n")

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for sym, data in self.equities.items():
            self.tree.insert("", "end", values=(sym, data["entry_price"], data["status"]))

    def save_equities(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.equities, f)

    def load_equities(self):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except:
            return {}
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()