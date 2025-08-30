# Vocabulary Website (Flask)

Two panels:
- **Admin Panel**: login, manage vocabulary (add/update/delete), bulk add up to 50 words at once from text, view user results.
- **User Panel**: start a 12-minute exam. Each question shows a **Bangla meaning**; user fills **Part of Speech** and **English word**. Each is 0.5 marks; total 1 per item. Results saved to JSON and shown at the end.

### Quick Start
1. **Install Python 3.10+**.
2. In a terminal:
   ```bash
   cd vocab-website-flask
   python -m venv .venv
   . .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python app.py
   ```
4. Open: http://127.0.0.1:5000

### Admin Login
- Default username: `admin`
- Default password: `changeme`
- To change, edit `data/config.json` (restart server after changes).

### Data Files
- Vocabulary store: `data/vocab.json`
- Quiz results: `data/results.json`
- Admin config: `data/config.json`

### Bulk Add Format (examples)
Paste up to ~50 lines like these:
```
Put (v.) – রাখা
Brave (adj.) - সাহসী
Advice (n.) — পরামর্শ
Truth (n.) – সত্য
Friendship (n.) - বন্ধুত্ব
```
Supported separators between English and Bangla: `-`, `–`, `—`.  
Part-of-speech accepted examples: `n.`, `noun`, `N`, `v`, `verb`, `adj`, `adjective`, `adv`, `adverb`, `pron`, `pronoun`, `prep`, `conj`, `interj` etc. The app normalizes to: `n.`, `v.`, `adj.`, `adv.`, `pron.`, `prep.`, `conj.`, `interj.`

### Notes
- This project uses **file-based storage** (JSON). No database server needed.
- Designed for PC/Laptop screens; mobile layout is not optimized.
- Modern, clean UI with custom CSS (no external CDNs required).
