import json
import os
import re
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

PROMPT = """
You are a warm, articulate, and engaging morning financial news anchor delivering a rapid-fire market briefing.

Structure & Timing:
- Total target runtime: Around 3 minutes 30 seconds.
- intro: A polite, energetic morning welcome to traders (maximum 20 words).
- stories: Exactly 10 distinct, major market updates.
  - Each story text MUST be strictly 40 to 45 words long (2 to 3 spoken sentences).
  - Sentence 1: The key event or corporate headline.
  - Sentence 2: Concrete figures (price, percentage, target, or valuation).
  - Sentence 3: The practical takeaway for the day's session.
  - search_query: A clear 2-to-3 word visual search term for stock video representing the industry/topic (e.g., "gold bullion vault", "oil refinery flame", "corporate skyscrapers", "shipping cargo ship", "software office desk").
- outro: A warm, professional sign-off reminding traders to trade with disciplined risk and follow for tomorrow's briefing (maximum 20 words).

Strict Rules:
1. Speak naturally like a TV presenter, not like reading a dry print article.
2. NEVER repeat generic phrases, boilerplates, or lines about "market analysts watching support zones" or "institutional liquidity dictates the trend".
3. Every story must contain completely unique, factual content.
4. Output strictly valid JSON with NO markdown formatting or backticks:
{
  "intro": "Good morning traders, here is your quick briefing on the top ten financial triggers you need to know before taking your positions today.",
  "stories": [
    {
      "headline": "Armee Infotech Debuts Today",
      "script": "Armee Infotech is scheduled to list on the exchanges today following strong subscription demand. The three hundred crore rupee initial public offering saw robust bidding from institutional buyers. Market participants will be watching opening premiums closely for early listing gains.",
      "search_query": "software office tech"
    }
  ],
  "outro": "That wraps up your market opening intelligence. Trade with disciplined risk, and follow for tomorrow's briefing."
}
"""

def generate_broadcast_script(news_headlines: list) -> dict:
    model = genai.GenerativeModel("gemini-1.5-flash")
    user_content = "Today's top headlines:\n" + "\n".join(news_headlines[:15])
    
    response = model.generate_content([PROMPT, user_content])
    raw_text = response.text.strip()
    
    # Strip any stray markdown wrapping
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        
    return json.loads(raw_text.strip())
    
